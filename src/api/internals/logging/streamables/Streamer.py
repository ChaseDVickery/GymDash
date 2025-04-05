from abc import abstractmethod
from src.api.internals.logging.streamables.StreamerRegistry import StreamerRegistry
from src.api.internals.logging.streamables.StreamableStat import StreamableStat
from typing import Dict, Any, SupportsFloat, List

class Streamer:
    def __init__(self, name: str, source_reader):
        self.name = name
        self.source_reader = source_reader
        self._source_exists = False
        self.keys: List[str] = []
        self.streamed: Dict[str, StreamableStat] = {}
        if not StreamerRegistry.register(self.name, self):
            raise KeyError(f"Cannot register streamer with name '{self.name}' because it already exists in the registry")
        
    def set_source_reader(self, new_reader):
        self.source_reader = new_reader
        self._source_exists = False
        self.streamed.clear()

    # https://github.com/tensorflow/tensorboard/blob/master/tensorboard/backend/event_processing/event_accumulator.py#L940
    @abstractmethod
    def check_source(self):
        pass
    
    def get_all_recent(self):
        if self.check_source():
            self.source_reader.Reload()
            return {key: self.streamed[key].get_recent() for key in self.keys}
        return {key: [] for key in self.keys}

    def get_recent_from_key(self, key:str):
        if self.check_source():
            self.source_reader.Reload()
            return self.streamed[key].get_recent()
        
    def get_recent_from_tag(self, tag:str):
        raise NotImplementedError("get_recent_from_tag not implemented")
        # if self.check_source():
        #     self.source_reader.Reload()
        #     return self.streamed[key].get_recent()