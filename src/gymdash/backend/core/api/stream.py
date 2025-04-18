from abc import abstractmethod
from typing import Dict, Any, List

class StreamableStat:
    """
    Class represents an easily appendable stat.
    This specializes in appending new information and
    tracking the last accessed datapoint to minimize
    data transactions when accessing newly-acquired data.
    """
    def __init__(self):
        self._last_read_index = -1
        self.reset()

    def reset(self):
        self.clear_values()
        self._last_read_index = -1

    def get_recent(self):
        """
        Returns all new values that have not yet been read.
        Modifies the internal read index.
        """
        start_idx = self._last_read_index + 1
        end_idx = len(self.get_values())
        self._last_read_index = end_idx - 1

        return self.get_values()[start_idx:end_idx]
    
    def __getitem__(self, idx):
        return self.get_values()[idx]
    
    def __str__(self) -> str:
        return f"StreamableStat(last_read={self._last_read_index}, values={self.get_values()})"
    
    def __repr__(self) -> str:
        return str(self.get_values())
        
    @abstractmethod
    def clear_values(self):
        raise NotImplementedError()
    
    @abstractmethod
    def get_values(self):
        raise NotImplementedError()

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
        

class StreamerRegistry:
    # Static mapper to track tb streamers
    log_map = {}
    @staticmethod
    def clear():
        StreamerRegistry.log_map.clear()
    @staticmethod
    def get_streamer(tb_log: str):
        return StreamerRegistry.log_map[tb_log] if tb_log in StreamerRegistry.log_map else None
    @staticmethod
    def _get_or_register(tb_log: str, streamer: Any):
        retrieved = StreamerRegistry.get_streamer(tb_log)
        if retrieved:
            print(f"Got existing streamer from '{tb_log}'")
            return retrieved
        else:
            if StreamerRegistry.register(tb_log, streamer):
                print(f"Registered new streamer to '{tb_log}'")
                return streamer
            else:
                raise ValueError(f"No existing streamer with name '{tb_log}' found, but unable to register")
    @staticmethod
    def get_or_register(streamer: Any):
        return StreamerRegistry._get_or_register(streamer.streamer_name, streamer)
    @staticmethod
    def register(tb_log: str, streamer: Any):
        if (tb_log in StreamerRegistry.log_map):
            return False
        StreamerRegistry.log_map[tb_log] = streamer
        print(f"Register streamer '{tb_log}'")
        return True
    @staticmethod
    def items():
        return StreamerRegistry.log_map.items()
    @staticmethod
    def streamers():
        return StreamerRegistry.log_map.values()