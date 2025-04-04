from abc import abstractmethod

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