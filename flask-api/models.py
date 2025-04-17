from pydantic import BaseModel, Field
from typing import List, Dict, Union, Optional, Tuple
from mcp.types import TextContent

# Models for tool inputs and outputs
class StepsInput(BaseModel):
    steps: List[str] = Field(..., description="List of reasoning steps")

class CalculationInput(BaseModel):
    expression: str = Field(..., description="Math expression to verify")
    expected: float = Field(..., description="Expected result")

class MathInput(BaseModel):
    a: float = Field(..., description="First number")
    b: float = Field(..., description="Second number")

class SingleNumberInput(BaseModel):
    a: float = Field(..., description="Input number")

class ListInput(BaseModel):
    l: List[float] = Field(..., description="List of numbers")

class StringInput(BaseModel):
    string: str = Field(..., description="Input string")

class ConsistencyStepInput(BaseModel):
    steps: List[Tuple[str, float]] = Field(..., description="List of calculation steps with results")

class ToolOutput(BaseModel):
    content: Union[List[TextContent], TextContent]
    success: bool = True
    error: Optional[str] = None