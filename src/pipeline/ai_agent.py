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
        current_store: str | None = None,
    ):
        self.extracted_files = extracted_files
        self.current_store = current_store
        self.df_daily_revenue = df_daily_revenue
        self.df_amount_unique_users = df_amount_unique_users
        self.df_unique_sets_of_authors = df_unique_sets_of_authors
        self.df_most_popular_author = df_most_popular_author
        self.df_top_customer_by_spending = df_top_customer_by_spending

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

    @staticmethod
    def _resolve_column(frame: pd.DataFrame, requested_column: str) -> str | None:
        normalized_requested = requested_column.strip().casefold()
        return next(
            (
                column for column in frame.columns
                if str(column).strip().casefold() == normalized_requested
            ),
            None,
        )

    def _calculate_data_tool(
        self,
        store_name: str,
        dataset: str,
        operation: str,
        column: str | None = None,
        date_range: dict[str, str] | None = None,
        filters: list[dict[str, str]] | None = None,
    ) -> str:
        if not isinstance(store_name, str) or not store_name.strip():
            return json.dumps({"error": "A valid store_name is required."})

        target_store = next(
            (
                name for name in self.extracted_files
                if name.strip().casefold() == store_name.strip().casefold()
            ),
            None,
        )
        if target_store is None:
            return json.dumps({"error": f"Store '{store_name}' was not found in extracted data."})

        if not isinstance(dataset, str) or dataset.strip().lower() not in {
            "orders", "books", "users",
        }:
            return json.dumps({"error": "dataset must be orders, books, or users."})
        dataset = dataset.strip().lower()
        dataframes = self.extracted_files[target_store]
        if dataset not in dataframes:
            return json.dumps({
                "error": f"Dataset '{dataset}' is not available for store '{target_store}'."
            })

        if not isinstance(operation, str):
            return json.dumps({"error": "A supported calculation operation is required."})
        operation = operation.strip().lower()
        supported_operations = {"count", "distinct_count", "sum", "mean", "min", "max"}
        if operation not in supported_operations:
            return json.dumps({
                "error": f"operation must be one of: {', '.join(sorted(supported_operations))}."
            })

        frame = dataframes[dataset].copy()
        if date_range is not None:
            if not isinstance(date_range, dict):
                return json.dumps({"error": "date_range must specify a column and date bounds."})
            date_column = date_range.get("column")
            start_date = date_range.get("start")
            end_date = date_range.get("end")
            if not all(isinstance(value, str) and value.strip() for value in (
                date_column, start_date, end_date
            )):
                return json.dumps({
                    "error": "date_range requires non-empty column, start, and end values."
                })
            resolved_date_column = self._resolve_column(frame, date_column)
            if resolved_date_column is None:
                return json.dumps({
                    "error": f"Date column '{date_column}' was not found in dataset '{dataset}'."
                })
            try:
                start = pd.Timestamp(start_date)
                end = pd.Timestamp(end_date)
                if start.tzinfo is None:
                    start = start.tz_localize("UTC")
                else:
                    start = start.tz_convert("UTC")
                if end.tzinfo is None:
                    end = end.tz_localize("UTC")
                else:
                    end = end.tz_convert("UTC")
                start = start.normalize()
                end = end.normalize()
            except (TypeError, ValueError):
                return json.dumps({"error": "date_range start and end must be valid dates."})
            if start > end:
                return json.dumps({"error": "date_range start must not be after end."})

            dates = pd.to_datetime(frame[resolved_date_column], errors="coerce", utc=True)
            frame = frame.loc[(dates >= start) & (dates < end + pd.Timedelta(days=1))]

        if filters is not None:
            if not isinstance(filters, list):
                return json.dumps({"error": "filters must be a list of filter conditions."})
            for condition in filters:
                if not isinstance(condition, dict):
                    return json.dumps({"error": "Each filter must specify column, operator, and value."})
                filter_column = condition.get("column")
                filter_operator = condition.get("operator")
                filter_value = condition.get("value")
                if not all(isinstance(value, str) and value.strip() for value in (
                    filter_column, filter_operator, filter_value
                )):
                    logger.info(
                        "AI Agent calculated %s on %s.%s for store %s across %s rows",
                        operation,
                        dataset,
                        column or "rows",
                        target_store,
                        len(frame),
                    )
                    return json.dumps({
                        "error": "Each filter requires non-empty column, operator, and value."
                    })
                resolved_column = self._resolve_column(frame, filter_column)
                if resolved_column is None:
                    return json.dumps({
                        "error": f"Filter column '{filter_column}' was not found in dataset '{dataset}'."
                    })
                series = frame[resolved_column].astype("string")
                normalized_operator = filter_operator.strip().lower()
                if normalized_operator == "equals":
                    mask = series.str.casefold() == filter_value.strip().casefold()
                elif normalized_operator == "contains":
                    mask = series.str.contains(
                        filter_value, case=False, regex=False, na=False
                    )
                elif normalized_operator == "starts_with":
                    mask = series.str.casefold().str.startswith(
                        filter_value.strip().casefold(), na=False
                    )
                else:
                    return json.dumps({
                        "error": "Filter operator must be equals, contains, or starts_with."
                    })
                frame = frame.loc[mask]

        if operation == "count":
            result: int | float = int(len(frame))
        else:
            if not isinstance(column, str) or not column.strip():
                return json.dumps({
                    "error": f"column is required for the {operation} operation."
                })
            resolved_column = self._resolve_column(frame, column)
            if resolved_column is None:
                return json.dumps({
                    "error": f"Column '{column}' was not found in dataset '{dataset}'."
                })
            if operation == "distinct_count":
                result = int(frame[resolved_column].nunique(dropna=True))
            else:
                numeric_values = pd.to_numeric(frame[resolved_column], errors="coerce").dropna()
                if numeric_values.empty:
                    return json.dumps({
                        "error": (
                            f"Column '{resolved_column}' has no numeric values to "
                            f"calculate {operation}."
                        )
                    })
                calculated = {
                    "sum": numeric_values.sum,
                    "mean": numeric_values.mean,
                    "min": numeric_values.min,
                    "max": numeric_values.max,
                }[operation]()
                result = calculated.item() if hasattr(calculated, "item") else calculated

        return json.dumps({
            "store": target_store,
            "dataset": dataset,
            "operation": operation,
            "column": column if operation != "count" else None,
            "matching_rows": int(len(frame)),
            "result": result,
        })


    def ask_agent(self, user_question: str) -> str:
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
                "name": "calculate_from_extracted_data",
                "description": (
                    "Perform a calculation on a store's extracted orders, books, or users "
                    "data when no precomputed aggregation answers the question. Supports "
                    "count, distinct_count, sum, mean, min, and max. Can restrict rows to "
                    "an inclusive date range or apply literal column filters. Never infer "
                    "a result without calling this tool."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "store_name": {"type": "string"},
                        "dataset": {"type": "string", "enum": ["orders", "books", "users"]},
                        "operation": {
                            "type": "string",
                            "enum": ["count", "distinct_count", "sum", "mean", "min", "max"],
                        },
                        "column": {
                            "type": ["string", "null"],
                            "description": "Required except for count.",
                        },
                        "date_range": {
                            "type": ["object", "null"],
                            "properties": {
                                "column": {"type": "string"},
                                "start": {"type": "string", "description": "Inclusive ISO date."},
                                "end": {"type": "string", "description": "Inclusive ISO date."},
                            },
                            "required": ["column", "start", "end"],
                        },
                        "filters": {
                            "type": ["array", "null"],
                            "items": {
                                "type": "object",
                                "properties": {
                                    "column": {"type": "string"},
                                    "operator": {
                                        "type": "string",
                                        "enum": ["equals", "contains", "starts_with"],
                                    },
                                    "value": {"type": "string"},
                                },
                                "required": ["column", "operator", "value"],
                            },
                        },
                    },
                    "required": ["store_name", "dataset", "operation"],
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
        store_schemas = {
            store_name: {
                dataset_name: {
                    column: str(frame[column].dtype)
                    for column in frame.columns
                }
                for dataset_name, frame in datasets.items()
            }
            for store_name, datasets in self.extracted_files.items()
        }
        system_message = {
            "role": "system",
            "content": (
                f"The currently selected store is '{self.current_store}'. "
                "Use precomputed retrieval tools for the existing dashboard aggregations. "
                "For any other question requiring a calculation on records, call "
                "calculate_from_extracted_data and use its returned result; do not estimate "
                "or invent results. For order counts within a date range, select dataset "
                "'orders', operation 'count', and the orders timestamp column. Date range "
                "bounds are inclusive calendar dates. Only use supported operations and "
                "actual dataset columns. If a request cannot be represented by the "
                "available calculation tool or the tool returns an error, explain the "
                "limitation/error to the user. Available store dataset columns and data "
                f"types: {json.dumps(store_schemas, default=str)}"
            ),
        }

        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[system_message, {"role": "user", "content": user_question}],
                tools=tools
            )

            message = response.choices[0].message

            if message.tool_calls:
                follow_up_messages = [
                    system_message,
                    {"role": "user", "content": user_question},
                    message,
                ]
                for tool_call in message.tool_calls:
                    tool_handler = tool_handlers.get(tool_call.function.name)
                    if tool_call.function.name == "calculate_from_extracted_data":
                        args = json.loads(tool_call.function.arguments)
                        query_result = self._calculate_data_tool(
                            store_name=args.get("store_name") or self.current_store or "",
                            dataset=args.get("dataset"),
                            operation=args.get("operation"),
                            column=args.get("column"),
                            date_range=args.get("date_range"),
                            filters=args.get("filters"),
                        )
                        follow_up_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": query_result,
                        })
                        continue

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