from abc import abstractmethod
from StreamableStat import StreamableStat
from StatSyncer import StatSyncer

class TensorboardStatSyncer(StatSyncer):
    def __init__(self) -> None:
        self.streamable: StreamableStat = None

    def parse_to_stream(self, filename):
        """
        Reads in and attempts to parse file contents
        to a more easily streamable structure
        """
        pass

    def get_scalars(self):
        pass