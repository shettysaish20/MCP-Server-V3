import asyncio
from typing import Any, Dict, Optional, List
import logging
from google import genai

logger = logging.getLogger(__name__)

class ActionLayer:
    def __init__(self):
        self.timeout_seconds = 30
        self.client = None

    def set_llm_client(self, client: Any) -> None:
        """Set the LLM client (Gemini)"""
        self.client = client

    async def execute_action(
        self,
        action_type: str,
        action_params: Optional[Dict[str, Any]],
        memory_layer: Any,
        perception_layer: Any
    ) -> str:
        """
        Execute the decided action using MCP tools or LLM generation
        """
        if action_type == "function_call":
            return await self._handle_function_call(action_params, memory_layer, perception_layer)
        elif action_type == "final_answer":
            return action_params["response"]
        elif action_type == "retry":
            return await self._generate_retry(memory_layer)
        elif action_type == "error":
            return f"Error: {action_params.get('message', 'Unknown error')}"
        elif action_type == "finish":
            responses = memory_layer.get_iteration_responses()
            return "Reached maximum iterations. History:\n" + "\n".join(responses)
        else:
            return f"Unknown action type: {action_type}"

    async def _handle_function_call(
        self,
        action_params: Dict[str, Any],
        memory_layer: Any,
        perception_layer: Any
    ) -> str:
        """Handle execution of MCP tool function calls"""
        function_name = action_params["function_name"]
        param_parts = action_params["param_parts"]
        
        try:
            # Parse the parameters
            params = await perception_layer.parse_function_call_params(param_parts)
            
            # Get the session and tools
            session = memory_layer.get_mcp_session()
            tools = memory_layer.get_tools()
            
            if not tools:
                return "Error: Tools not initialized"

            # Find the tool by name
            tool = next((t for t in tools if getattr(t, 'name', '') == function_name), None)
            if not tool:
                return f"Unknown function: {function_name}"

            # Execute the tool
            result = await session.call_tool(function_name, params)
            
            # Handle the result based on its structure
            if hasattr(result, 'content'):
                if isinstance(result.content, list):
                    # Handle list of content items
                    content_texts = []
                    for item in result.content:
                        if hasattr(item, 'text'):
                            content_texts.append(item.text)
                        else:
                            content_texts.append(str(item))
                    return str(content_texts)
                elif hasattr(result.content, 'text'):
                    # Handle single content item
                    return result.content.text
                else:
                    # Handle raw content
                    return str(result.content)
            else:
                # Handle raw result
                return str(result)
            
        except Exception as e:
            # logger.error(f"Error executing function {function_name}: {str(e)}")
            return f"Error executing function {function_name}: {str(e)}"

    async def _generate_retry(self, memory_layer: Any) -> str:
        """Generate a new response using the LLM"""
        if not self.client:
            raise ValueError("LLM client not initialized")
            
        try:
            prompt = memory_layer.get_system_prompt()
            
            async def generate():
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
                return response.text.strip()

            # Use asyncio.wait_for to implement timeout
            result = await asyncio.wait_for(generate(), timeout=self.timeout_seconds)
            return result
            
        except asyncio.TimeoutError:
            return "Error: LLM generation timed out"
        except Exception as e:
            logger.error(f"Error in LLM generation: {str(e)}")
            return f"Error in LLM generation: {str(e)}"