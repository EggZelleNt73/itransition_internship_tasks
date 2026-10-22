import os
import json
import pandas as pd
from openai import AzureOpenAI
from src.types import StoreDataCollection
from src.logger import get_logger


logger = get_logger(__name__)

AggregationResult = pd.DataFrame | int | str
StoreAggregation = dict[str, AggregationResult]


class DataAppAgent:
    def __init__(
        self,
        extracted_files: StoreDataCollection,
        df_daily_revenue: dict[str, pd.DataFrame],
        df_amount_unique_users: dict[str, int],
        df_unique_sets_of_authors: dict[str, int],
        df_most_popular_author: dict[str, str],
        df_top_customer_by_spending: dict[str, pd.DataFrame],
        current_store: str,
    ):
        self.extracted_files = extracted_files
        self.current_store = current_store
        self.df_daily_revenue = df_daily_revenue
        self.df_amount_unique_users = df_amount_unique_users
        self.df_unique_sets_of_authors = df_unique_sets_of_authors
        self.df_most_popular_author = df_most_popular_author
        self.df_top_customer_by_spending = df_top_customer_by_spending
        self.last_filter_result: dict[str, str | int | pd.DataFrame] | None = None
        self.filter_action_requested = False

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

        if (not endpoint) or (not api_key) or (not self.deployment_name):
            raise ValueError("Missing Azure OpenAI configuration environment variables.")

        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2024-08-01-preview"
        )


    def _get_aggregation_tool(
        self,
        store_name: str,
        aggregation: StoreAggregation,
        aggregation_name: str,
    ) -> str:
        target_key = store_name.upper().strip()
        normalized_aggregation = {k.upper().strip(): v for k, v in aggregation.items()}

        if target_key not in normalized_aggregation:
            return json.dumps({
                "error": f"Store mapping for '{store_name}' was not found in {aggregation_name} data."
            })

        result = normalized_aggregation[target_key]
        if isinstance(result, pd.DataFrame):
            return result.to_json(orient="records")
        return json.dumps(result)


    def _get_revenue_tool(self, store_name: str) -> str:
        return self._get_aggregation_tool(
            store_name, self.df_daily_revenue, "daily revenue"
        )

    def _get_unique_users_tool(self, store_name: str) -> str:
        return self._get_aggregation_tool(
            store_name, self.df_amount_unique_users, "unique users"
        )

    def _get_unique_author_sets_tool(self, store_name: str) -> str:
        return self._get_aggregation_tool(
            store_name, self.df_unique_sets_of_authors, "unique author sets"
        )

    def _get_most_popular_author_tool(self, store_name: str) -> str:
        return self._get_aggregation_tool(
            store_name, self.df_most_popular_author, "most popular author"
        )

    def _get_top_customer_by_spending_tool(self, store_name: str) -> str:
        return self._get_aggregation_tool(
            store_name, self.df_top_customer_by_spending, "top customer by spending"
        )

    def _filter_data_tool(
        self,
        store_name: str,
        dataset: str,
        column: str,
        operator: str,
        values: list[str] | None = None,
        match_values_from: dict[str, str] | None = None,
    ) -> str:
        self.last_filter_result = None
        if not all(
            isinstance(value, str) and value.strip()
            for value in (store_name, dataset, column, operator)
        ):
            return json.dumps({
                "error": "A valid store_name, dataset, column, and operator are required."
            })
        if match_values_from is not None and not isinstance(match_values_from, dict):
            return json.dumps({"error": "match_values_from must specify a dataset and column."})

        normalized_dataset = dataset.strip().lower()
        if normalized_dataset not in {"books", "users", "orders"}:
            return json.dumps({"error": "Dataset must be books, users, or orders."})

        target_store = next(
            (
                name for name in self.extracted_files
                if name.upper().strip() == store_name.upper().strip()
            ),
            None,
        )
        if target_store is None:
            return json.dumps({"error": f"Store '{store_name}' was not found."})

        dataframes = self.extracted_files[target_store]
        if normalized_dataset not in dataframes:
            return json.dumps({
                "error": f"Dataset '{normalized_dataset}' is not available for store '{target_store}'."
            })

        frame = dataframes[normalized_dataset]
        target_column = self._resolve_column(frame, column)
        if target_column is None:
            return json.dumps({
                "error": f"Column '{column}' was not found in dataset '{normalized_dataset}'."
            })

        normalized_operator = operator.strip().lower()
        supported_operators = {"contains", "not_contains", "starts_with", "ends_with", "equals"}
        if normalized_operator not in supported_operators:
            return json.dumps({
                "error": f"Operator must be one of: {', '.join(sorted(supported_operators))}."
            })

        if (values is None) == (match_values_from is None):
            return json.dumps({
                "error": "Provide either a non-empty values list or match_values_from, but not both."
            })

        if match_values_from is not None:
            source_dataset_value = match_values_from.get("dataset")
            source_column_value = match_values_from.get("column")
            if not isinstance(source_dataset_value, str) or not isinstance(
                source_column_value, str
            ):
                return json.dumps({
                    "error": "match_values_from must specify a valid dataset and column."
                })
            source_dataset = source_dataset_value.strip().lower()
            if source_dataset not in {"books", "users", "orders"}:
                return json.dumps({
                    "error": "Reference dataset must be books, users, or orders."
                })
            if source_dataset not in dataframes:
                return json.dumps({
                    "error": f"Reference dataset '{source_dataset}' is not available for store '{target_store}'."
                })
            source_frame = dataframes[source_dataset]
            source_column = self._resolve_column(
                source_frame, source_column_value
            )
            if source_column is None:
                return json.dumps({
                    "error": (
                        f"Reference column '{source_column_value}' "
                        f"was not found in dataset '{source_dataset}'."
                    )
                })
            match_values = (
                source_frame[source_column]
                .dropna()
                .astype(str)
                .loc[lambda items: items.str.strip().ne("")]
                .unique()
                .tolist()
            )
        else:
            if not isinstance(values, list) or not all(
                isinstance(value, str) and value.strip() for value in values
            ):
                return json.dumps({"error": "values must be a non-empty list of strings."})
            match_values = [value.strip() for value in values]

        search_values = [value.casefold() for value in match_values]
        if not search_values:
            return json.dumps({"error": "No usable values were found for the filter."})

        text_values = frame[target_column].astype("string")
        if normalized_operator == "equals":
            mask = text_values.str.casefold().isin(search_values)
        else:
            matcher = {
                "contains": lambda value: text_values.str.contains(
                    value, case=False, regex=False, na=False
                ),
                "not_contains": lambda value: text_values.str.contains(
                    value, case=False, regex=False, na=False
                ),
                "starts_with": lambda value: text_values.str.casefold().str.startswith(
                    value, na=False
                ),
                "ends_with": lambda value: text_values.str.casefold().str.endswith(
                    value, na=False
                ),
            }[normalized_operator]
            mask = pd.Series(False, index=frame.index)
            for value in search_values:
                mask |= matcher(value)
            if normalized_operator == "not_contains":
                mask = ~mask

        filtered_frame = frame.loc[mask].copy()
        self.last_filter_result = {
            "store_name": target_store,
            "dataset": normalized_dataset,
            "column": target_column,
            "row_count": len(filtered_frame),
            "dataframe": filtered_frame,
        }
        logger.info(
            "AI Agent filtered %s rows from %s.%s in store %s",
            len(filtered_frame),
            normalized_dataset,
            target_column,
            target_store,
        )
        return json.dumps({
            "store": target_store,
            "dataset": normalized_dataset,
            "matching_rows": len(filtered_frame),
            "result": "The matching rows are displayed in the dashboard's AI-filtered data section.",
        })

    @staticmethod
    def _resolve_column(frame: pd.DataFrame, requested_column: str) -> str | None:
        normalized_requested = requested_column.strip().casefold()
        return next(
            (column for column in frame.columns if str(column).strip().casefold() == normalized_requested),
            None,
        )


    def ask_agent(self, user_question: str) -> str:
        self.filter_action_requested = False
        tool_definitions = [
            ("get_store_revenue", "Retrieves historical daily revenue for a store."),
            ("get_store_unique_users", "Retrieves the total unique user count for a store."),
            ("get_store_unique_author_sets", "Retrieves the count of unique author sets for a store."),
            ("get_store_most_popular_author", "Retrieves the most popular author for a store."),
            (
                "get_store_top_customer_by_spending",
                "Retrieves the top customer by spending for a store.",
            ),
        ]
        tools = [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "store_name": {"type": "string", "description": "The target store name string, e.g. STORE1"}
                        },
                        "required": ["store_name"],
                    },
                },
            }
            for name, description in tool_definitions
        ]
        tools.append({
            "type": "function",
            "function": {
                "name": "filter_store_data",
                "description": (
                    "Filter rows from a store's books, users, or orders dataset using a "
                    "literal text condition. Use values for explicit alternatives, or "
                    "match_values_from to match against values in another dataset, such "
                    "as book titles containing user names. This updates a dedicated "
                    "filtered-data table without changing dashboard metrics."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "store_name": {
                            "type": "string",
                            "description": "Store to filter; defaults to the currently selected dashboard store.",
                        },
                        "dataset": {
                            "type": "string",
                            "enum": ["books", "users", "orders"],
                        },
                        "column": {
                            "type": "string",
                            "description": "Column in the dataset to filter.",
                        },
                        "operator": {
                            "type": "string",
                            "enum": ["contains", "not_contains", "starts_with", "ends_with", "equals"],
                        },
                        "values": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "One or more literal values; alternatives are ORed.",
                        },
                        "match_values_from": {
                            "type": "object",
                            "properties": {
                                "dataset": {
                                    "type": "string",
                                    "enum": ["books", "users", "orders"],
                                },
                                "column": {"type": "string"},
                            },
                            "required": ["dataset", "column"],
                        },
                    },
                    "required": ["dataset", "column", "operator"],
                },
            },
        })
        tool_handlers = {
            "get_store_revenue": self._get_revenue_tool,
            "get_store_unique_users": self._get_unique_users_tool,
            "get_store_unique_author_sets": self._get_unique_author_sets_tool,
            "get_store_most_popular_author": self._get_most_popular_author_tool,
            "get_store_top_customer_by_spending": self._get_top_customer_by_spending_tool,
        }

        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"The currently selected dashboard store is '{self.current_store}'. "
                            "Use filter_store_data when the user requests a row-level filter "
                            "or selection rather than an existing aggregate. For filters, use "
                            "only the supplied datasets, columns, and literal-match operators. "
                            "Match values from another dataset when the request refers to "
                            "values such as people names."
                        ),
                    },
                    {"role": "user", "content": user_question},
                ],
                tools=tools
            )

            message = response.choices[0].message

            if message.tool_calls:
                follow_up_messages = [
                    {
                        "role": "system",
                        "content": (
                            f"The currently selected dashboard store is '{self.current_store}'. "
                            "Row-level filters appear in the AI-filtered data table and do not "
                            "change existing dashboard metrics."
                        ),
                    },
                    {"role": "user", "content": user_question},
                    message,
                ]
                for tool_call in message.tool_calls:
                    if tool_call.function.name == "filter_store_data":
                        self.filter_action_requested = True
                        args = json.loads(tool_call.function.arguments)
                        store_name = args.get("store_name") or self.current_store
                        if not isinstance(store_name, str):
                            query_result = json.dumps({"error": "A valid store_name is required."})
                        else:
                            query_result = self._filter_data_tool(
                                store_name=store_name,
                                dataset=args.get("dataset", ""),
                                column=args.get("column", ""),
                                operator=args.get("operator", ""),
                                values=args.get("values"),
                                match_values_from=args.get("match_values_from"),
                            )
                        follow_up_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": query_result,
                        })
                        continue

                    tool_handler = tool_handlers.get(tool_call.function.name)
                    if tool_handler is None:
                        query_result = json.dumps({"error": "Unknown data retrieval tool."})
                    else:
                        args = json.loads(tool_call.function.arguments)
                        store_name = args.get("store_name")
                        logger.info(
                            f"AI Agent triggered {tool_call.function.name} for store: {store_name}"
                        )
                        if not isinstance(store_name, str):
                            query_result = json.dumps(
                                {"error": "A valid store_name is required."}
                            )
                        else:
                            query_result = tool_handler(store_name)
                    follow_up_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": query_result,
                    })

                final_response = self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=follow_up_messages,
                )
                return final_response.choices[0].message.content or ""

            return message.content or ""
            
        except Exception as e:
            logger.error(f"Failed to execute conversational response from Azure OpenAI: {e}", exc_info=True)
            return "An internal calculation tracing issue occurred inside the AI module."