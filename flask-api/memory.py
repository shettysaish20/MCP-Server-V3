from typing import Any, List, Optional, Dict

class MemoryLayer:
    def __init__(self):
        self.user_preferences: Optional[Dict[str, Any]] = None
        self.last_response = None
        self.iteration = 0
        self.iteration_response: List[str] = []
        self.max_iterations = 20
        self.tools = None
        self.system_prompt = None
        self.mcp_session = None

    def store_user_preferences(self, preferences: Dict[str, Any]) -> None:
        """Store user preferences in memory"""
        self.user_preferences = preferences

    def get_user_preferences(self) -> Optional[Dict[str, Any]]:
        """Retrieve stored user preferences"""
        return self.user_preferences

    def has_preferences(self) -> bool:
        """Check if user preferences are set"""
        return self.user_preferences is not None

    def reset_state(self) -> None:
        """Reset iteration state"""
        self.last_response = None
        self.iteration = 0
        self.iteration_response = []

    def add_iteration_response(self, response: str) -> None:
        """Add a response to the iteration history"""
        self.iteration_response.append(response)

    def increment_iteration(self) -> None:
        """Increment the iteration counter"""
        self.iteration += 1

    def get_iteration_count(self) -> int:
        """Get current iteration count"""
        return self.iteration

    def get_iteration_responses(self) -> List[str]:
        """Get all iteration responses"""
        return self.iteration_response

    def set_last_response(self, response: Any) -> None:
        """Set the last response"""
        self.last_response = response

    def get_last_response(self) -> Any:
        """Get the last response"""
        return self.last_response

    def store_tools(self, tools: Any) -> None:
        """Store MCP tools"""
        self.tools = tools

    def get_tools(self) -> Any:
        """Get stored MCP tools"""
        return self.tools

    def store_system_prompt(self, prompt: str) -> None:
        """Store system prompt"""
        self.system_prompt = prompt

    def get_system_prompt(self) -> str:
        """Get stored system prompt"""
        return self.system_prompt

    def store_mcp_session(self, session: Any) -> None:
        """Store MCP session"""
        self.mcp_session = session

    def get_mcp_session(self) -> Any:
        """Get stored MCP session"""
        return self.mcp_session

    def should_continue(self) -> bool:
        """Check if iterations should continue"""
        return self.iteration < self.max_iterations