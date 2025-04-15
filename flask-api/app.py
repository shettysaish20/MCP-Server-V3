from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import asyncio
from google import genai
import json
from functools import partial
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask with async support
app = Flask(__name__)
CORS(app)

# Initialize Gemini client
api_key = os.getenv("GEMINI_API_KEY")
genai_client = genai.Client(api_key=api_key)

# Global variables for MCP session
mcp_session = None
tools = None
system_prompt = None

def get_or_create_event_loop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

async def initialize_mcp():
    """Initialize MCP server and session"""
    global mcp_session, tools, system_prompt
    
    logger.info("Establishing connection to MCP server...")
    try:
        # Get absolute path to mcp_server.py
        current_dir = os.path.dirname(os.path.abspath(__file__))
        server_path = os.path.join(current_dir, "mcp_server.py")
        
        server_params = StdioServerParameters(
            command="python",
            args=[server_path]
        )
        
        # Create and store the client context managers
        client = stdio_client(server_params)
        read_stream, write_stream = await client.__aenter__()
        
        # Create the session
        session = ClientSession(read_stream, write_stream)
        await session.__aenter__()
        
        try:
            await session.initialize()
            
            # Get available tools
            tools_result = await session.list_tools()
            tools = tools_result.tools
            
            # Create system prompt
            tools_description = create_tools_description(tools)
            system_prompt = create_system_prompt(tools_description)
            
            # Store session globally
            mcp_session = session
            logger.info("MCP server initialized successfully")
            return session, client
            
        except Exception as e:
            # Clean up if initialization fails
            await session.__aexit__(type(e), e, e.__traceback__)
            await client.__aexit__(type(e), e, e.__traceback__)
            raise
            
    except Exception as e:
        logger.error(f"Error initializing MCP server: {str(e)}")
        raise

def create_tools_description(tools):
    """Create description of available tools"""
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
            tools_description.append(f"{i+1}. Error processing tool")
            
    return "\n".join(tools_description)

def create_system_prompt(tools_description):
    """Create the system prompt for the LLM"""
    return f"""You are a math agent solving complex math expressions step-by-step.
    Available Tools:
    {tools_description}
    
    You must respond with EXACTLY ONE LINE in one of these formats (no additional text):
    1. For function calls:
    FUNCTION_CALL: {{"name": function_name, "arguments": {{"param1": value1, "param2": value2}}}}
    2. For final answers:
    FINAL_ANSWER: <NUMBER>
    
    Instructions:
    - Start by calling the show_reasoning tool ONLY ONCE with steps.
    - Use all available math tools to solve the problem step-by-step.
    - Apply BODMAS rules: start with innermost parentheses.
    - Verify each calculation with verify_calculation tool.
    - Finally verify consistency with verify_consistency tool.
    - Submit final result as FINAL_ANSWER: <NUMBER>"""

async def process_math_expression(expression):
    """Process a math expression using MCP tools"""
    global mcp_session, tools, system_prompt
    
    # Initialize MCP if not already initialized
    if mcp_session is None:
        await initialize_mcp()
    
    iteration = 0
    last_response = None
    iteration_response = []
    max_iterations = 30
    final_answer = None
    
    while iteration < max_iterations:
        try:
            # Prepare current query
            if last_response is None:
                current_query = expression
            else:
                current_query = current_query + "\n\n" + " ".join(iteration_response)
                current_query = current_query + "  What should you do next?"

            # Get LLM response
            response = await get_llm_response(current_query)
            
            # Process response
            if response.startswith("FUNCTION_CALL:"):
                result = await handle_function_call(response)
                iteration_response.append(result)
                last_response = result
            elif response.startswith("FINAL_ANSWER:"):
                final_answer = response.split(":", 1)[1].strip()
                break
                
            iteration += 1
            
        except Exception as e:
            return {"error": str(e)}
            
    return {"result": final_answer if final_answer else "No result found"}

async def get_llm_response(query):
    """Get response from LLM with timeout"""
    try:
        response = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: genai_client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=f"{system_prompt}\n\nQuery: {query}"
                )
            ),
            timeout=10
        )
        return response.text.strip()
    except asyncio.TimeoutError:
        raise Exception("LLM request timed out")

async def handle_function_call(response):
    """Handle a function call from the LLM"""
    global mcp_session, tools
    
    _, function_info = response.split(":", 1)
    function_info = json.loads(function_info.strip())
    
    func_name = function_info.get("name")
    params = function_info.get("arguments", {})
    
    # Call the tool
    result = await mcp_session.call_tool(func_name, arguments=params)
    
    # Format result
    if hasattr(result, 'content'):
        if isinstance(result.content, list):
            return [item.text if hasattr(item, 'text') else str(item) for item in result.content]
        return str(result.content)
    return str(result)

@app.route('/api/evaluate', methods=['POST'])
def evaluate_expression():
    """API endpoint to evaluate math expressions"""
    try:
        data = request.get_json()
        expression = data.get('expression')
        
        if not expression:
            return jsonify({"error": "No expression provided"}), 400
            
        loop = get_or_create_event_loop()
        result = loop.run_until_complete(process_math_expression(expression))
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing expression: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    return jsonify({"message": "Flask API is working!"})

if __name__ == '__main__':
    # Initialize event loop and MCP server before starting Flask
    loop = get_or_create_event_loop()
    session = None
    client = None
    
    try:
        # Initialize MCP server and store the context managers
        session, client = loop.run_until_complete(initialize_mcp())
        logger.info("Starting Flask server...")
        app.run(debug=True, port=5000)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
    finally:
        # Clean up resources
        if session and client:
            try:
                loop.run_until_complete(session.__aexit__(None, None, None))
                loop.run_until_complete(client.__aexit__(None, None, None))
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")
        loop.close()