
from typing import Dict, Any
from pydantic import BaseModel

class SimulationStartConfig(BaseModel):
    name: str
    kwargs: Dict[str, Any] = {}