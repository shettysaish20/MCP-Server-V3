import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
from google import genai
from concurrent.futures import TimeoutError
# from functools import partial
# import json
import ast
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask with CORS
app = Flask(__name__)
CORS(app)

# Load environment variables from .env file
load_dotenv()

# Access your API key and initialize Gemini client correctly
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

max_iterations = 20
last_response = None
iteration = 0
iteration_response = []

# Global variables for MCP session
mcp_session = None
tools = None
system_prompt = None


async def parse_function_call_params(param_parts: list[str]) -> dict:
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


async def generate_with_timeout(client, prompt, timeout=10):
    """Generate content with a timeout"""
    print("Starting LLM generation...")
    try:
        # Convert the synchronous generate_content call to run in a thread
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None, 
                lambda: client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
            ),
            timeout=timeout
        )
        print("LLM generation completed")
        return response
    except TimeoutError:
        print("LLM generation timed out!")
        raise
    except Exception as e:
        print(f"Error in LLM generation: {e}")
        raise

def reset_state():
    """Reset all global variables to their initial state"""
    global last_response, iteration, iteration_response
    last_response = None
    iteration = 0
    iteration_response = []

def get_or_create_event_loop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

@app.route('/api/evaluate', methods=['POST'])
def evaluate_math_expression():
    """API endpoint to evaluate math expressions"""
    try:
        data = request.get_json()
        expression = data.get('expression')
        
        if not expression:
            return jsonify({"error": "No expression provided"}), 400
            
        loop = get_or_create_event_loop()
        result = loop.run_until_complete(main(expression))
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing expression: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    return jsonify({"message": "Flask API is working!"})

async def main(expression=None):
    reset_state()  # Reset at the start of main
    logger.info("Starting main execution...")
    try:
        # Create a single MCP server connection
        logger.info("Establishing connection to MCP server...")
        
        # Get absolute path to mcp_server.py
        current_dir = os.path.dirname(os.path.abspath(__file__))
        server_path = os.path.join(current_dir, "mcp_server.py")
        
        server_params = StdioServerParameters(
            command="python",
            args=[server_path]
        )

        async with stdio_client(server_params) as (read, write):
            logger.info("Connection established, creating session...")
            async with ClientSession(read, write) as session:
                logger.info("Session created, initializing...")
                await session.initialize()
                
                # Get available tools
                logger.info("Requesting tool list...")
                tools_result = await session.list_tools()
                tools = tools_result.tools
                print(f"Successfully retrieved {len(tools)} tools")

                # Create system prompt with available tools
                print("Creating system prompt...")
                print(f"Number of tools: {len(tools)}")
                
                try:
                    # First, let's inspect what a tool object looks like
                    # if tools:
                    #     print(f"First tool properties: {dir(tools[0])}")
                    #     print(f"First tool example: {tools[0]}")
                    
                    tools_description = []
                    for i, tool in enumerate(tools):
                        try:
                            # Get tool properties
                            params = tool.inputSchema
                            desc = getattr(tool, 'description', 'No description available')
                            name = getattr(tool, 'name', f'tool_{i}')
                            
                            # Format the input schema in a more readable way
                            if 'properties' in params:
                                param_details = []
                                for param_name, param_info in params['properties'].items():
                                    param_type = param_info.get('type', 'unknown')
                                    param_details.append(f"{param_name}: {param_type}")
                                params_str = ', '.join(param_details)
                            else:
                                params_str = 'no parameters'

                            tool_desc = f"{i+1}. {name}({params_str}) - {desc}"
                            tools_description.append(tool_desc)
                            print(f"Added description for tool: {tool_desc}")
                        except Exception as e:
                            logger.error(f"Error processing tool {i}: {e}")
                            tools_description.append(f"{i+1}. Error processing tool")
                    
                    tools_description = "\n".join(tools_description)
                    print("Successfully created tools description")
                except Exception as e:
                    logger.error(f"Error creating tools description: {e}")
                    tools_description = "Error loading tools"
                
                print("Created system prompt...")
                
                system_prompt = f"""
                You are a math agent solving complex math expressions step-by-step.
                You have access to various mathematical tools for calculations and verifications.

                Available Tools:
                {tools_description}

                You must respond with EXACTLY ONE LINE in one of these formats (no additional text):

                1. For function calls:
                FUNCTION_CALL: function_name|input.param1=value1|input.param2=value2|...

                    - You can also use nested keys for structured inputs (e.g., input.string, input.int_list).
                    - For list-type inputs, use square brackets: input.int_list=[73,78,68,73,65]

                2. For final answers:
                FINAL_ANSWER: <NUMBER>

                Instructions:
                - Start by calling the show_reasoning tool ONLY ONCE with a list of all step-by-step reasoning steps explaining how you will solve the problem. Once called, NEVER CALL IT AGAIN UNDER ANY CIRCUMSTANCES.
                - When reasoning, tag each step with the reasoning type (e.g., [Arithmetic], [Logical Check]).
                - Use all available math tools to solve the problem step-by-step.
                - When a function returns multiple values, process all of them.
                - Apply BODMAS rules: start with the innermost parentheses and work outward.
                - Do not skip steps — perform all calculations sequentially.
                - Respond only with one line at a time.
                - Call only one tool per response.
                - After calculating a number, verify it by calling:
                FUNCTION_CALL: verify_calculation|input.expression=<MATH_EXPRESSION>|input.expected=<NUMBER>
                - If verify_calculation returns False, re-evaluate your previous steps.
                - Once you reach a final answer, check for consistency of all steps and calculations by calling:
                FUNCTION_CALL: verify_consistency|input.steps=[[<MATH_EXPRESSION1>, <ANSWER1>], [<MATH_EXPRESSION2>, <ANSWER2>], ...]
                - If verify_consistency returns False, re-evaluate your previous steps.
                - Once verify_consistency return True, submit your final result as:
                FINAL_ANSWER: <NUMBER>

                
                ✅ Examples:
                - FUNCTION_CALL: add|input.a=5|input.b=3
                - FUNCTION_CALL: show_reasoning|input.steps=["First, add 2 and 20. [Arithmetic]", "Then, the result is the final answer. [Final Answer]"]
                - FUNCTION_CALL: strings_to_chars_to_int|input.string=INDIA
                - FUNCTION_CALL: int_list_to_exponential_sum|input.int_list=[73,78,68,73,65]
                - FINAL_ANSWER: 42


                Strictly follow the above guidelines.
                Your entire response should always be a single line starting with either FUNCTION_CALL: or FINAL_ANSWER:"""


                ## verify_consistency part-
                # - Once you reach a final answer, check for consistency of all steps and calculations by calling:
                # FUNCTION_CALL: {{"name": "verify_consistency", "arguments": {{"steps": (<MATH_EXPRESSION1>, <ANSWER1>), (<MATH_EXPRESSION2>, <ANSWER2>), ...}}}}
                # - If verify_consistency returns False, re-evaluate your previous steps.

                # 3. For calling any paint tools:
                # USE_PAINT: {{"name": function_name, "arguments": {{"param1": value1, "param2": value2}}}}
                # Commented out example for testing
                # Examples:
                # User: Solve (2 + 3) * 4
                # Assistant: FUNCTION_CALL: show_reasoning|["1. First, solve inside parentheses: 2 + 3", "2. Then multiply the result by 4"]
                # User: Next step?
                # Assistant: FUNCTION_CALL: add|2 + 3
                # User: Result is 5. Let's verify this step.
                # Assistant: FUNCTION_CALL: verify|2 + 3|5
                # User: Verified. Next step?
                # Assistant: FUNCTION_CALL: calculate|5 * 4
                # User: Result is 20. Let's verify the final answer.
                # Assistant: FUNCTION_CALL: verify|(2 + 3) * 4|20
                # User: Verified correct.
                # Assistant: FINAL_ANSWER: [20]

                # query = """Solve ((3000 - (400+552)) / 2 + 1024"""
                print("Starting iteration loop...")
                
                # Use global iteration variables
                global iteration, last_response
                final_answer = None
                
                while iteration < max_iterations:
                    print(f"\n--- Iteration {iteration + 1} ---")
                    if last_response is None:
                        current_query = expression
                    else:
                        current_query = current_query + "\n\n" + " ".join(iteration_response)
                        current_query = current_query + "  What should you do next? Do not generate any additional text."

                    # Get model's response with timeout
                    print("Preparing to generate LLM response...")
                    prompt = f"{system_prompt}\n\nQuery: {current_query}"
                    try:
                        response = await generate_with_timeout(client, prompt)
                        response_text = response.text.strip()
                        print(f"LLM Response: {response_text}")
                        
                        # Find the FUNCTION_CALL line in the response
                        for line in response_text.split('\n'):
                            line = line.strip()
                            if (line.startswith("FUNCTION_CALL:")): # or line.startswith("USE_PAINT:")):
                                response_text = line
                                break
                        
                    except Exception as e:
                        print(f"Failed to get LLM response: {e}")
                        break


                    if response_text.startswith("FUNCTION_CALL:"): # or response_text.startswith("USE_PAINT:"):
                        _, function_info = response_text.split(":", 1)
                        parts = [p.strip() for p in function_info.split("|")]
                        func_name, param_parts = parts[0], parts[1:]

                        print(f"\nDEBUG: Raw function info: {function_info}")
                        print(f"DEBUG: Split parts: {parts}")
                        print(f"DEBUG: Function name: {func_name}")
                        print(f"DEBUG: Raw parameters: {param_parts}")

                        try:
                            tool = next((t for t in tools if t.name == func_name), None)
                            if not tool:
                                print(f"DEBUG: Available tools: {[t.name for t in tools]}")
                                raise ValueError(f"Unknown tool: {func_name}")

                            print(f"DEBUG: Found tool: {tool.name}")
                            print(f"DEBUG: Tool schema: {tool.inputSchema}")

                            arguments = await parse_function_call_params(param_parts)
                            print(f"DEBUG: Final arguments: {arguments}")
                            print(f"DEBUG: Calling tool {func_name}")

                            result = await session.call_tool(func_name, arguments=arguments)
                            print(f"DEBUG: Raw result: {result}")

                            if hasattr(result, 'content'):
                                print(f"DEBUG: Result has content attribute")
                                if isinstance(result.content, list):
                                    iteration_result = [
                                        item.text if hasattr(item, 'text') else str(item)
                                        for item in result.content
                                    ]
                                else:
                                    iteration_result = str(result.content)
                            else:
                                print(f"DEBUG: Result has no content attribute")
                                iteration_result = str(result)

                            print(f"DEBUG: Final iteration result: {iteration_result}")

                            result_str = f"[{', '.join(iteration_result)}]" if isinstance(iteration_result, list) else str(iteration_result)

                            iteration_response.append(
                                f"In the {iteration + 1} iteration you called {func_name} with {arguments} parameters, "
                                f"and the function returned {result_str}."
                            )
                            last_response = iteration_result

                        except Exception as e:
                            print(f"DEBUG: Error details: {str(e)}")
                            print(f"DEBUG: Error type: {type(e)}")
                            import traceback
                            traceback.print_exc()
                            iteration_response.append(f"Error in iteration {iteration + 1}: {str(e)}")
                            break


                    elif response_text.startswith("FINAL_ANSWER:"):
                        print("\n=== Agent Execution Complete ===")
                        final_answer = response_text.split(":", 1)[1].strip()
                        break

                    iteration += 1

                return {"result": final_answer if final_answer else "No result found"}

    except Exception as e:
        print(f"Error in main execution: {e}")
        import traceback
        traceback.print_exc()
    finally:
        reset_state()  # Reset at the end of main

if __name__ == "__main__":
    logger.info("Starting Flask server...")
    app.run(debug=True, port=5000)


