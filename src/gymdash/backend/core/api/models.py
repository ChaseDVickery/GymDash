from collections.abc import Callable
from datetime import datetime
from uuid import UUID
from typing import Any, Dict, Iterable, List, Tuple, Union
import json

from pydantic import BaseModel


class SimulationStartConfig(BaseModel):
    name:       str
    sim_key:    str
    sim_family: str             = None
    sim_type:   str             = None
    kwargs:     Dict[str, Any]  = {}

    class Encoder(json.JSONEncoder):
        def default(self, o: Any) -> Any:
            print("ENCODING SIMULATIONSTARTCONFIG")
            print(o)
            print(o.__dict__)
            return o.__dict__
    def custom_decoder(obj):
        if "name" in obj and \
        "sim_key" in obj and \
        "sim_family" in obj and \
        "sim_type" in obj and \
        "kwargs" in obj:
            family = obj["sim_family"] if "sim_family" in obj else None
            sim_type = obj["sim_type"] if "sim_type" in obj else None
            kwargs = obj["kwargs"] if "kwargs" in obj else {}
            return SimulationStartConfig(
                name=obj["name"],
                sim_key=obj["sim_key"],
                sim_family=family,
                sim_type=sim_type,
                kwargs=kwargs,
            )
        else:
            return obj
        
class SimulationIDModel(BaseModel):
    id:         UUID

class StatQuery(BaseModel):
    id:         UUID    # Simulation ID
    tags:       List[str]   = [] # tag types to include
    keys:       List[str]   = [] # keys to include
    exclusion_mode: bool    = False # exclusion mode

class StoredSimulationInfo(BaseModel):
    name:       str                     = None
    sim_id:     UUID                    = None
    created:    Union[datetime, None]   = None
    started:    Union[datetime, None]   = None
    ended:      Union[datetime, None]   = None
    is_done:    bool                    = False
    cancelled:  bool                    = False
    failed:     bool                    = False
    config:     SimulationStartConfig

class InteractorChannelModel(BaseModel):
    triggered:  bool                = False
    value:      Union[str, None]    = None

    def __str__(self) -> str:
        return f"ICM(triggered={self.triggered}, value={self.value})"

class SimulationInteractionModel(BaseModel):
    """
    Represents a query from the client to the server
    to interact with or query a running simulation
    """
    # ID really should be a UUID
    id:                 str
    timeout:            float                               = 0.0
    # Interaction channels
    stop_simulation:    Union[InteractorChannelModel,None]  = None
    progress:           Union[InteractorChannelModel,None]  = None
    is_done:            Union[InteractorChannelModel,None]  = None
    cancelled:          Union[InteractorChannelModel,None]  = None
    failed:             Union[InteractorChannelModel,None]  = None

    error_details:      Union[InteractorChannelModel,None]  = None

    @property
    def channels(self) -> List[Tuple[str, InteractorChannelModel]]:
        return [
            ("stop_simulation", self.stop_simulation),
            ("progress",        self.progress),
            ("is_done",         self.is_done),
            ("cancelled",       self.cancelled),
            ("failed",          self.failed),
            ("error_details",   self.error_details),
        ]
    @property
    def triggered_channels(self) -> Iterable[Tuple[str, InteractorChannelModel]]:
        return filter(lambda channel: channel[1] is not None and channel[1].triggered, self.channels)
    
    def __str__(self) -> str:
        return f"SimulationInteractionModel(id={self.id}, timeout={self.timeout}, channels=(stop_simulation={str(self.stop_simulation)}, progress={str(self.progress)}, is_done={str(self.is_done)}, cancelled={str(self.cancelled)}, failed={str(self.failed)}))"