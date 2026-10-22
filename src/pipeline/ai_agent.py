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
    ):
        self.extracted_files = extracted_files
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
                messages=[{"role": "user", "content": user_question}],
                tools=tools
            )

            message = response.choices[0].message

            if message.tool_calls:
                follow_up_messages = [
                    {"role": "user", "content": user_question},
                    message,
                ]
                for tool_call in message.tool_calls:
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