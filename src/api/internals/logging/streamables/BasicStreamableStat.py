from StreamableStat import StreamableStat

class BasicStreamableStat(StreamableStat):
    """
    Class represents an easily appendable stat.
    This specializes in appending new information and
    tracking the last accessed datapoint to minimize
    data transactions when accessing newly-acquired data.
    """
    def __init__(self):
        super().__init__()
        self.values = []

    def append(self, value):
        """Appends a new value to the log."""
        self.values.append(value)

    def extend(self, value):
        """Extends the value log with input values."""
        self.values.extend(value)
    
    def sync_to(self, full_data):
        if (len(full_data) > len(self.values)):
            # Copy all the values after the last of my current values
            self.extend(full_data[len(self.get_values()):])
        else:
            raise ValueError("Input data was shorter than currently known streamable values list.")
    
    def __str__(self) -> str:
        return f"BasicStreamableStat(last_read={self._last_read_index}, values={self.get_values()})"
    
    def get_values(self):
        return self.values
    
    def clear_values(self):
        self.values.clear()