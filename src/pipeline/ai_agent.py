import os
import json
from openai import AzureOpenAI
from src.pipeline.aggregations import apply_aggregation
from src.types import StoreDataCollection
from src.logger import get_logger


logger = get_logger(__name__)


class DataAppAgent:
    def __init__(self, extracted_files: StoreDataCollection, df_daily_revenue: dict):
        self.extracted_files = extracted_files
        self.df_daily_revenue = df_daily_revenue

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


    def _get_revenue_tool(self, store_name: str) -> str:
        target_key = store_name.upper().strip()
        normalized_revenue = {k.upper().strip(): v for k, v in self.df_daily_revenue.items()}

        if target_key in normalized_revenue:
            return normalized_revenue[target_key].to_json(orient="records")
        return json.dumps({"error": f"Store mapping for '{store_name}' was not found in data allocation grids."})


    def ask_agent(self, user_question: str) -> str:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_store_revenue",
                    "description": "Retrieves the historical daily revenue dataset for a specified store identifier.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "store_name": {"type": "string", "description": "The target store name string, e.g. STORE1"}
                        },
                        "required": ["store_name"],
                    },
                },
            }
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": user_question}],
                tools=tools
            )

            message = response.choices[0].message

            if message.tool_calls:
                for tool_call in message.tool_calls:
                    if tool_call.function.name == "get_store_revenue":
                        args = json.loads(tool_call.function.arguments)
                        logger.info(f"AI Agent triggered tool execution for store: {args.get('store_name')}")
                        query_result = self._get_revenue_tool(args.get("store_name"))
                        final_response = self.client.chat.completions.create(
                            model=self.deployment_name,
                            messages=[
                                {"role": "user", "content": user_question},
                                message,
                                {"role": "tool", "tool_call_id": tool_call.id, "content": query_result}
                            ]
                        )
                        return final_response.choices[0].message.content
                        
            return message.content
            
        except Exception as e:
            logger.error(f"Failed to execute conversational response from Azure OpenAI: {e}", exc_info=True)
            return "An internal calculation tracing issue occurred inside the AI module."