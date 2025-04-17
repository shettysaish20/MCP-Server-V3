import asyncio
from typing import Dict, Any, Tuple, Optional

class DecisionLayer:
    def __init__(self):
        pass

    async def determine_next_action(
        self,
        response_type: str,
        function_parts: list,
        raw_response: str,
        memory_layer: Any
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Determines the next action based on LLM response and memory state
        Returns: (action_type, action_params)
        """
        # Check if we've exceeded max iterations
        if not memory_layer.should_continue():
            return "finish", None

        # Store the response for history
        memory_layer.add_iteration_response(raw_response)
        
        # If it's a function call, prepare the parameters for action
        if response_type == "function_call":
            if len(function_parts) < 1:
                return "error", {"message": "Invalid function call format"}
                
            function_name = function_parts[0]
            param_parts = function_parts[1:] if len(function_parts) > 1 else []
            
            return "function_call", {
                "function_name": function_name,
                "param_parts": param_parts
            }
            
        # If it's a final answer, prepare to return it
        elif response_type == "final_answer":
            return "final_answer", {"response": raw_response}
            
        # For unknown responses, try to recover by generating again
        else:
            return "retry", None

    def check_prerequisites(self, memory_layer: Any) -> Tuple[bool, Optional[str]]:
        """
        Check if all prerequisites are met before processing
        Returns: (is_ready, error_message)
        """
        if not memory_layer.has_preferences():
            return False, "User preferences must be set before processing"
        
        if not memory_layer.get_tools():
            return False, "MCP tools not initialized"
            
        if not memory_layer.get_system_prompt():
            return False, "System prompt not set"
            
        return True, None