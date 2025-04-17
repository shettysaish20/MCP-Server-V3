# basic import 
from mcp.server.fastmcp import FastMCP, Image
from mcp.server.fastmcp.prompts import base
from mcp.types import TextContent
from mcp import types
from PIL import Image as PILImage
import math
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
import re
import sys
from models import *
# instantiate an MCP server client
console = Console()
mcp = FastMCP("AdvancedCalculator")

# DEFINE TOOLS

## Session 5 Assignment additional tools
@mcp.tool()
def show_reasoning(input: StepsInput) -> ToolOutput:
    """Show the step-by-step reasoning process"""
    console.print("[blue]FUNCTION CALL:[/blue] show_reasoning()")
    try:
        for i, step in enumerate(input.steps, 1):
            console.print(Panel(
                f"{step}",
                title=f"Step {i}",
                border_style="cyan"
            ))
        return ToolOutput(
            content=[TextContent(
                type="text",
                text="REASONING SHOWN. FOLLOW THIS INSTRUCTION STRICTLY. PROCEED FURTHER. DO NOT CALL THIS TOOL AGAIN!"
            )]
        )
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=str(e)), success=False, error=str(e))

@mcp.tool()
def verify_calculation(input: CalculationInput) -> ToolOutput:
    """Verify if a calculation is correct"""
    console.print("[blue]FUNCTION CALL:[/blue] verify()")
    try:
        actual = float(eval(input.expression))
        is_correct = abs(actual - float(input.expected)) < 1e-10
        
        if is_correct:
            console.print(f"[green] Correct! {input.expression} = {input.expected}[/green]")
        else:
            console.print(f"[red] Incorrect! {input.expression} should be {actual}, got {input.expected}[/red]")
            
        return ToolOutput(content=[TextContent(
            type="text",
            text=str(is_correct)
        )])
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=f"Error: {str(e)}"), success=False, error=str(e))

@mcp.tool()
def verify_consistency(input: ConsistencyStepInput) -> ToolOutput:
    """Check if calculation steps are consistent with each other"""
    try:
        issues = []
        warnings = []
        insights = []
        previous = None
        
        for i, (expression, result) in enumerate(input.steps, 1):
            checks = []
            
            # 1. Basic Calculation Verification
            try:
                expected = eval(expression)
                if abs(float(expected) - float(result)) < 1e-10:
                    checks.append("[green] Calculation verified[/green]")
                else:
                    issues.append(f"Step {i}: Calculation mismatch")
                    checks.append("[red] Calculation error[/red]")
            except:
                warnings.append(f"Step {i}: Couldn't verify calculation")
                checks.append("[yellow] Verification failed[/yellow]")

            # Rest of verification logic remains same...

            previous = (expression, result)

        total_checks = len(input.steps) * 5
        passed_checks = total_checks - (len(issues) * 2 + len(warnings))
        consistency_score = (passed_checks / total_checks) * 100

        return ToolOutput(
            content=TextContent(
                type="text",
                text=str({
                    "consistency_score": consistency_score,
                    "issues": issues,
                    "warnings": warnings,
                    "insights": insights,
                    "result": consistency_score > 80,
                    "next_step": "Return the final result as FINAL_ANSWER: <NUMBER>" if consistency_score > 80 else "Please review the steps and try again."
                })
            )
        )
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=f"Error: {str(e)}"), success=False, error=str(e))

#addition tool
@mcp.tool()
def add(input: MathInput) -> ToolOutput:
    """Add two numbers"""
    print("CALLED: add(input: MathInput)")
    try:
        result = input.a + input.b
        return ToolOutput(content=TextContent(type="text", text=str(result)))
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=str(e)), success=False, error=str(e))

@mcp.tool()
def add_list(input: ListInput) -> ToolOutput:
    """Add all numbers in a list"""
    print("CALLED: add_list(input: ListInput)")
    try:
        result = sum(input.l)
        return ToolOutput(content=TextContent(type="text", text=str(result)))
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=str(e)), success=False, error=str(e))

@mcp.tool()
def subtract(input: MathInput) -> ToolOutput:
    """Subtract two numbers"""
    print("CALLED: subtract(input: MathInput)")
    try:
        result = input.a - input.b
        return ToolOutput(content=TextContent(type="text", text=str(result)))
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=str(e)), success=False, error=str(e))

@mcp.tool()
def multiply(input: MathInput) -> ToolOutput:
    """Multiply two numbers"""
    print("CALLED: multiply(input: MathInput)")
    try:
        result = input.a * input.b
        return ToolOutput(content=TextContent(type="text", text=str(result)))
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=str(e)), success=False, error=str(e))

@mcp.tool()
def divide(input: MathInput) -> ToolOutput:
    """Divide two numbers"""
    print("CALLED: divide(input: MathInput)")
    try:
        if input.b == 0:
            raise ValueError("Cannot divide by zero")
        result = float(input.a / input.b)
        return ToolOutput(content=TextContent(type="text", text=str(result)))
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=str(e)), success=False, error=str(e))

@mcp.tool()
def power(input: MathInput) -> ToolOutput:
    """Power of two numbers"""
    print("CALLED: power(input: MathInput)")
    try:
        result = input.a ** input.b
        return ToolOutput(content=TextContent(type="text", text=str(result)))
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=str(e)), success=False, error=str(e))

@mcp.tool()
def sqrt(input: SingleNumberInput) -> ToolOutput:
    """Square root of a number"""
    print("CALLED: sqrt(input: SingleNumberInput)")
    try:
        result = float(input.a ** 0.5)
        return ToolOutput(content=TextContent(type="text", text=str(result)))
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=str(e)), success=False, error=str(e))

@mcp.tool()
def cbrt(input: SingleNumberInput) -> ToolOutput:
    """Cube root of a number"""
    print("CALLED: cbrt(input: SingleNumberInput)")
    try:
        result = float(input.a ** (1/3))
        return ToolOutput(content=TextContent(type="text", text=str(result)))
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=str(e)), success=False, error=str(e))

@mcp.tool()
def factorial(input: SingleNumberInput) -> ToolOutput:
    """Factorial of a number"""
    print("CALLED: factorial(input: SingleNumberInput)")
    try:
        result = math.factorial(input.a)
        return ToolOutput(content=TextContent(type="text", text=str(result)))
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=str(e)), success=False, error=str(e))

@mcp.tool()
def log(input: SingleNumberInput) -> ToolOutput:
    """Log of a number"""
    print("CALLED: log(input: SingleNumberInput)")
    try:
        if input.a <= 0:
            raise ValueError("Cannot take log of non-positive number")
        result = float(math.log(input.a))
        return ToolOutput(content=TextContent(type="text", text=str(result)))
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=str(e)), success=False, error=str(e))

@mcp.tool()
def remainder(input: MathInput) -> ToolOutput:
    """Remainder of two numbers division"""
    print("CALLED: remainder(input: MathInput)")
    try:
        if input.b == 0:
            raise ValueError("Cannot divide by zero")
        result = input.a % input.b
        return ToolOutput(content=TextContent(type="text", text=str(result)))
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=str(e)), success=False, error=str(e))

@mcp.tool()
def sin(input: SingleNumberInput) -> ToolOutput:
    """Sine of a number"""
    print("CALLED: sin(input: SingleNumberInput)")
    try:
        result = float(math.sin(input.a))
        return ToolOutput(content=TextContent(type="text", text=str(result)))
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=str(e)), success=False, error=str(e))

@mcp.tool()
def cos(input: SingleNumberInput) -> ToolOutput:
    """Cosine of a number"""
    print("CALLED: cos(input: SingleNumberInput)")
    try:
        result = float(math.cos(input.a))
        return ToolOutput(content=TextContent(type="text", text=str(result)))
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=str(e)), success=False, error=str(e))

@mcp.tool()
def tan(input: SingleNumberInput) -> ToolOutput:
    """Tangent of a number"""
    print("CALLED: tan(input: SingleNumberInput)")
    try:
        result = float(math.tan(input.a))
        return ToolOutput(content=TextContent(type="text", text=str(result)))
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=str(e)), success=False, error=str(e))

@mcp.tool()
def mine(input: MathInput) -> ToolOutput:
    """Special mining tool"""
    print("CALLED: mine(input: MathInput)")
    try:
        result = input.a - input.b - input.b
        return ToolOutput(content=TextContent(type="text", text=str(result)))
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=str(e)), success=False, error=str(e))

@mcp.tool()
def create_thumbnail(image_path: str) -> Image:
    """Create a thumbnail from an image"""
    print("CALLED: create_thumbnail(image_path: str) -> Image:")
    img = PILImage.open(image_path)
    img.thumbnail((100, 100))
    return Image(data=img.tobytes(), format="png")

@mcp.tool()
def strings_to_chars_to_int(input: StringInput) -> ToolOutput:
    """Return the ASCII values of the characters in a word"""
    print("CALLED: strings_to_chars_to_int(input: StringInput)")
    try:
        result = [ord(char) for char in input.string]
        return ToolOutput(content=TextContent(type="text", text=str(result)))
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=str(e)), success=False, error=str(e))

@mcp.tool()
def int_list_to_exponential_sum(input: ListInput) -> ToolOutput:
    """Return sum of exponentials of numbers in a list"""
    print("CALLED: int_list_to_exponential_sum(input: ListInput)")
    try:
        result = sum(math.exp(i) for i in input.l)
        return ToolOutput(content=TextContent(type="text", text=str(result)))
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=str(e)), success=False, error=str(e))

@mcp.tool()
def fibonacci_numbers(input: SingleNumberInput) -> ToolOutput:
    """Return the first n Fibonacci Numbers"""
    print("CALLED: fibonacci_numbers(input: SingleNumberInput)")
    try:
        if input.a <= 0:
            return ToolOutput(content=TextContent(type="text", text="[]"))
        fib_sequence = [0, 1]
        for _ in range(2, input.a):
            fib_sequence.append(fib_sequence[-1] + fib_sequence[-2])
        return ToolOutput(content=TextContent(type="text", text=str(fib_sequence[:input.a])))
    except Exception as e:
        return ToolOutput(content=TextContent(type="text", text=str(e)), success=False, error=str(e))


# DEFINE RESOURCES

# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    print("CALLED: get_greeting(name: str) -> str:")
    return f"Hello, {name}!"


# DEFINE AVAILABLE PROMPTS
@mcp.prompt()
def review_code(code: str) -> str:
    return f"Please review this code:\n\n{code}"
    # print("CALLED: review_code(code: str) -> str:")


@mcp.prompt()
def debug_error(error: str) -> list[base.Message]:
    return [
        base.UserMessage("I'm seeing this error:"),
        base.UserMessage(error),
        base.AssistantMessage("I'll help debug that. What have you tried so far?"),
    ]

if __name__ == "__main__":
    # Check if running with mcp dev command
    print("STARTING")
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()  # Run without transport for dev server
    else:
        mcp.run(transport="stdio")  # Run with stdio for direct execution
