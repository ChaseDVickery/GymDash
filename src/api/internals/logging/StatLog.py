

class StatLog:
    def __init__(self):
        self.values = []
        self._last_read_index = -1
        self.reset()

    def reset(self):
        self.values.clear()
        self._last_read_index = -1

    def append(self, value):
        """Appends a new value to the log."""
        self.values.append(value)

    def extend(self, value):
        """Extends the value log with input values."""
        self.values.extend(value)

    def read_new_values(self):
        """
        Returns all new values that have not yet been read.
        Modifies the internal read index.
        """
        start_idx = self._last_read_index + 1
        end_idx = len(self.values) - 1
        self._last_read_index = end_idx

        return self.values[start_idx:end_idx]
        # return {
        #     "start":    start_idx,
        #     "end":      end_idx,
        #     "values":   self.values[start_idx:end_idx]
        # }
    
    def __getitem__(self, key):
        return self.values[key]
    
    def __str__(self) -> str:
        return f"StatLog(last_read={self._last_read_index}, values={self.values})"
    
    def __repr__(self) -> str:
        return str(self.values)