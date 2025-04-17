import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
from google import genai
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS

from perception import PerceptionLayer
from memory import MemoryLayer
from decision import DecisionLayer
from action import ActionLayer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask with CORS
app = Flask(__name__)
CORS(app)

# Load environment variables
load_dotenv()

def get_or_create_event_loop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

# Initialize layers and clients
memory_layer = MemoryLayer()
perception_layer = PerceptionLayer()
decision_layer = DecisionLayer()
action_layer = ActionLayer()

# Initialize Gemini client and set it in action layer
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)
action_layer.set_llm_client(client)

# Initialize MCP session on startup
async def init_app():
    """Initialize application state"""
    try:
        await initialize_session()
        logger.info("MCP session initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize MCP session: {e}")

# Run initialization
loop = get_or_create_event_loop()
loop.run_until_complete(init_app())

@app.route('/api/preferences', methods=['POST'])
def set_user_preferences():
    """API endpoint to set user preferences before starting the math solver"""
    try:
        preferences = request.get_json()
        if not perception_layer.validate_user_preferences(preferences):
            return jsonify({
                "error": "Invalid preferences format. Required fields: detail_level, notation_style, topics, decimal_places"
            }), 400
            
        memory_layer.store_user_preferences(preferences)
        return jsonify({"message": "Preferences stored successfully"})
        
    except Exception as e:
        logger.error(f"Error storing preferences: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/evaluate', methods=['POST'])
def evaluate_math_expression():
    """API endpoint to evaluate math expressions"""
    try:
        # Check if preferences are set
        if not memory_layer.has_preferences():
            return jsonify({
                "error": "User preferences not set. Please call /api/preferences first"
            }), 400
            
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
    """Main execution flow"""
    memory_layer.reset_state()
    logger.info("Starting main execution...")
    
    try:
        # Initialize session if not already done
        is_ready, error_msg = decision_layer.check_prerequisites(memory_layer)
        if not is_ready:
            await initialize_session()
            
        # Main execution loop
        current_query = expression
        final_answer = None
        
        while memory_layer.should_continue():
            logger.info(f"Iteration {memory_layer.get_iteration_count() + 1}")
            
            # Generate LLM response using action layer
            prompt = f"{memory_layer.get_system_prompt()}\n\nQuery: {current_query}"
            memory_layer.store_system_prompt(prompt)  # Update prompt in memory
            
            try:
                response_text = await action_layer._generate_retry(memory_layer)
                if not response_text:
                    logger.error("Empty response from LLM")
                    break
            except Exception as e:
                logger.error(f"Failed to get LLM response: {e}")
                break
                
            # Parse response
            response_type, function_parts, raw_response = perception_layer.parse_llm_response(response_text)
            
            # Determine next action
            action_type, action_params = await decision_layer.determine_next_action(
                response_type, function_parts, raw_response, memory_layer
            )
            
            # Execute action
            result = await action_layer.execute_action(
                action_type, action_params, memory_layer, perception_layer
            )
            
            if action_type == "final_answer":
                final_answer = action_params["response"]
                break
                
            memory_layer.increment_iteration()
            
            # Update query for next iteration
            if memory_layer.get_last_response():
                current_query = f"{expression}\n\n{' '.join(memory_layer.get_iteration_responses())}\nWhat should you do next?"
            
            memory_layer.set_last_response(result)

        return {"result": final_answer if final_answer else "No result found"}

    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        return {"error": str(e)}
    finally:
        memory_layer.reset_state()

async def initialize_session():
    """Initialize MCP session and tools"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    server_path = os.path.join(current_dir, "mcp_server.py")
    
    server_params = StdioServerParameters(
        command="python",
        args=[server_path]
    )

    async with stdio_client(server_params) as (read, write):
        logger.info("Connection established, creating session...")
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Get available tools
            tools_result = await session.list_tools()
            tools = tools_result.tools
            
            # Store session and tools in memory layer
            memory_layer.store_mcp_session(session)
            memory_layer.store_tools(tools)
            
            # Create and store system prompt
            system_prompt = create_system_prompt(tools)
            memory_layer.store_system_prompt(system_prompt)
            
            return session, tools

def create_system_prompt(tools) -> str:
    """Create system prompt with available tools"""
    try:
        tools_description = []
        for i, tool in enumerate(tools):
            try:
                params = tool.inputSchema
                desc = getattr(tool, 'description', 'No description available')
                name = getattr(tool, 'name', f'tool_{i}')
                
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
            except Exception as e:
                logger.error(f"Error processing tool {i}: {e}")
                tools_description.append(f"{i+1}. Error processing tool")
        
        tools_description = "\n".join(tools_description)
        
        return f"""
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
        Your entire response should always be a single line starting with either FUNCTION_CALL: or FINAL_ANSWER:
        """
    except Exception as e:
        logger.error(f"Error creating system prompt: {e}")
        return "Error loading tools"

if __name__ == "__main__":
    logger.info("Starting Flask server...")
    app.run(debug=True, port=5000)


