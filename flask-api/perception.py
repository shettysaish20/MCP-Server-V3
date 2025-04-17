import ast
import logging

logger = logging.getLogger(__name__)

class PerceptionLayer:
    def __init__(self):
        pass

    async def parse_function_call_params(self, param_parts: list[str]) -> dict:
        """
        Parses key=value parts from the FUNCTION_CALL format.
        Supports nested keys like input.string=foo and list values like input.int_list=[1,2,3]
        Returns a nested dictionary.
        """
        result = {}

        for part in param_parts:
            if "=" not in part:
                raise ValueError(f"Invalid parameter format (expected key=value): {part}")

            key, value = part.split("=", 1)

            # Try to parse as Python literal (int, float, list, etc.)
            try:
                parsed_value = ast.literal_eval(value)
            except Exception:
                parsed_value = value.strip()

            # Support nested keys like input.string
            keys = key.split(".")
            current = result
            for k in keys[:-1]:
                current = current.setdefault(k, {})
            current[keys[-1]] = parsed_value

        return result

    def parse_llm_response(self, response_text: str) -> tuple[str, list[str], str]:
        """
        Parse the LLM response to extract function calls or final answer
        Returns: (response_type, function_parts, raw_response)
        """
        response_text = response_text.strip()
        
        if response_text.startswith("FUNCTION_CALL:"):
            _, function_info = response_text.split(":", 1)
            parts = [p.strip() for p in function_info.split("|")]
            return "function_call", parts, response_text
        elif response_text.startswith("FINAL_ANSWER:"):
            return "final_answer", [], response_text.split(":", 1)[1].strip()
        else:
            return "unknown", [], response_text

    def validate_user_preferences(self, preferences: dict) -> bool:
        """
        Validates that user preferences contain required fields
        """
        required_fields = [
            'detail_level',  # e.g. 'basic', 'intermediate', 'advanced'
            'notation_style',  # e.g. 'standard', 'scientific'
            'topics',  # list of math topics
            'decimal_places'  # number of decimal places for results
        ]
        
        return all(field in preferences for field in required_fields)