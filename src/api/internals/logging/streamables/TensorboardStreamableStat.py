from .StreamableStat import StreamableStat
from tensorboard.backend.event_processing import event_accumulator, tag_types

class TensorboardStreamableStat(StreamableStat):
    """
    Class represents an easily appendable stat.
    This specializes in appending new information and
    tracking the last accessed datapoint to minimize
    data transactions when accessing newly-acquired data.
    """
    def __init__(self, accumulator: event_accumulator.EventAccumulator, key: str):
        super().__init__()
        if not accumulator:
            raise ValueError("TensorboardStreamableStat was not initialized with a proper EventAccumulator")
        self.ea             = accumulator
        self.key            = key
        self._key_exists    = False
        # if key not in self.ea.Tags(tag_types.SCALARS):
        #     raise KeyError(f"TensorboardStreamableStat, key '{key}' was not found in the EventAccumulator")

    @property
    def key_exists(self):
        if not self._key_exists:
            self._key_exists = self.key in self.ea.Tags()[tag_types.SCALARS]
        return self._key_exists

    def append(self, value):
        """Appends a new value to the log."""
        raise RuntimeError("TensorboardStreamableStat should only query the EventAccumulator, not update it.")

    def extend(self, value):
        """Extends the value log with input values."""
        raise RuntimeError("TensorboardStreamableStat should only query the EventAccumulator, not update it.")
    
    def sync_to(self, full_data):
        raise RuntimeError("TensorboardStreamableStat should only query the EventAccumulator, not update it.")
    
    def __str__(self) -> str:
        return f"BasicStreamableStat(last_read={self._last_read_index}, values={self.get_values()})"
    
    def _get_values(self):
        # return self.ea.Tags(tag_types.SCALARS)[self.key]
        return self.ea.Scalars(self.key)
    def get_values(self):
        self.ea.Reload()
        if self.key_exists:
            print(f"TensorboardStreamableStat has {len(self._get_values())} values: {self._get_values()}")
            return self._get_values()
        return []
    
    def clear_values(self):
        pass
        # raise RuntimeError("TensorboardStreamableStat should only query the EventAccumulator, not update it.")