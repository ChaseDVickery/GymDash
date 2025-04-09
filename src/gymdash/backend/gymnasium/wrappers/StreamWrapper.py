import csv
import json
import os
import time
from glob import glob
from typing import Any, Optional, SupportsFloat, Union, Dict, List
from tensorboard.backend.event_processing import event_accumulator, tag_types

from collections.abc import Callable

from ..StatLog import StatLog
from ..streamables.StreamableStat import StreamableStat
from ..streamables.TensorboardStreamableStat import TensorboardStreamableStat
from ..streamables.StreamerRegistry import StreamerRegistry
from src.api.internals.logging.streamables.Streamer import Streamer

import gymnasium as gym
import pandas
from gymnasium.core import ActType, ObsType

class StreamWrapper(gym.Wrapper):
    def __init__(
        self,
        env: gym.Env,
        keys: Union[List[str],None],
        tb_log: str                     = None
    ):
        super().__init__(env)
        self.tb_log_path: str                           = tb_log
        self._tb_exists: bool                           = False
        self._ea: event_accumulator.EventAccumulator    = None
        self.keys: List[str]                            = keys if keys else []

        self.streamed: Dict[str, TensorboardStreamableStat] = {}
        if not StreamerRegistry.register(self.tb_log_path, self):
            raise KeyError(f"Cannot register streamer with name '{tb_log}' because it already exists in the registry")
        
    def reset(self, **kwargs) -> tuple[Any, dict[str, Any]]:
        return self.env.reset(**kwargs)
    
    def render(self):
        return self.env.render()
    
    def close(self):
        return self.env.close()
    
    def step(self, action: Any) -> tuple[Any, SupportsFloat, bool, bool, dict[str, Any]]:
        return self.env.step(action)
    
    def set_log_path(self, new_path):
        self.tb_log_path = new_path
        self._tb_exists = False
        self.streamed.clear()

    # https://github.com/tensorflow/tensorboard/blob/master/tensorboard/backend/event_processing/event_accumulator.py#L940
    def check_tb(self):
        if (self._tb_exists): return True
        if (not self.tb_log_path): return False
        # Setup using new EventAccumulator
        self._ea = event_accumulator.EventAccumulator(
            self.tb_log_path
        )
        for key in self.keys:
            self.streamed[key] = TensorboardStreamableStat(self._ea, key)
        self._tb_exists = True
        return True
    
    def get_all_recent(self):
        if self.check_tb():
            self._ea.Reload()
            return {key: self._get_recent(key) for key in self.keys}
        return {key: [] for key in self.keys}

    def _get_recent(self, key:str):
        return self.streamed[key].get_recent()
        # scalars = self._ea.Tags()[tag_types.SCALARS]
        # print(f"Scalars= '{self._ea.Tags()[tag_types.SCALARS]}'")
        # print(f"Checking key '{key}' in scalar records")
        # if key in scalars:
        #     print(f"Found key '{key}' in scalar records")
        #     print(self._ea.Scalars(key))
        #     return self._ea.Scalars(key)
        # else:
        #     print(f"Missing key '{key}' in scalar records")
        #     return []

    def get_recent(self, key:str):
        if self.check_tb():
            self._ea.Reload()
            return self._get_recent(key)
            
