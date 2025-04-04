from abc import abstractmethod
from StreamableStat import StreamableStat

class StatSyncer:
    def __init__(self) -> None:
        self.streamable: StreamableStat = None

    @abstractmethod
    def parse_to_stream(self, filename):
        """
        Reads in and attempts to parse file contents
        to a more easily streamable structure
        """
        pass

    @abstractmethod
    def get_scalars(self):
        pass