import os
import re
import dataclasses
from pathlib import Path
from gymdash.backend.core.api.stream import StreamableStat
from typing import Union, Callable, Dict, Set
from gymdash.backend.core.api.config.stat_tags import ANY_TAG, MEDIA_TAG_SET
try:
    from tensorboard.backend.event_processing import event_accumulator, tag_types
    _has_tensorboard = True
except ImportError:
    _has_tensorboard = False
    

if not _has_tensorboard:
    raise ImportError("Install tensorboard to use MediaLinkStreamableStat.")

@dataclasses.dataclass(frozen=True)
class FileEvent:
    """Takes after tensorboard ImageEvent and AudioEvent, but
    reads from a source file

    Attributes:
      wall_time: Timestamp of the event in seconds.
      step: Global step of the event.
      encoded_string: Image content encoded in bytes.
      tag: The file type.
      src_name: The name of the source file.
    """
    wall_time: float
    step: int
    encoded_string: bytes
    tag: str
    src_name: str

class MediaLinkStreamableStat(StreamableStat):
    """
    Class represents an easily appendable stat.
    This specializes in appending new information and
    tracking the last accessed datapoint to minimize
    data transactions when accessing newly-acquired data.
    """
    def __init__(self, key: str, tag: str, media_folder: Union[str, Path], media_regex: str, step_extractor: Callable[[str], int]):
        """
        Initialize MediaLinkStreamableStat.

        Args:
            key: Stat key.
            tag: Tag for the stat. Represents the type of media (image, audio, etc.)
            media_folder: The base folder path where linked media is stored.
            media_regex: Regex string used to identify media files.
            step_extractor: Function used to parse media filenames to step/episode values.
                Thus every media file should contain means to find the step/episode
                for which it was recorded.
        """

        self.key = key
        self.tag = tag
        self.folder = media_folder
        self.pattern = re.compile(media_regex)
        self.step_extractor = step_extractor

        # A dict mapping step values to FileEvents
        self._detected: Dict[int, FileEvent] = dict()
        # A set of step values that have been modified since last recent access
        self._changed: Set[int] = set()

        super().__init__()

    @property
    def found_key_tag(self):
        return self.tag

    @property
    def key_exists(self):
        return True
    
    def __str__(self) -> str:
        return f"MediaLinkStreamableStat(last_read={self._last_read_index}, values={self.get_values()})"
    
    def _update_changed_files(self):
        print(f"MediaLinkStreamableStat _update_changed_files")
        print(f"MediaLinkStreamableStat folder: {os.path.abspath(self.folder)}")
        if os.path.exists(os.path.abspath(self.folder)):
            for filename in os.listdir(self.folder):
                match = self.pattern.search(filename)
                if match:
                    filepath = os.path.abspath(os.path.join(self.folder, filename))
                    modification_time = os.path.getmtime(filepath)
                    step = self.step_extractor(filename)
                    # If we already found a file at that step, then check if the
                    # last modification times match up. If the mod times are
                    # the same, then it hasn't changed, so move on...
                    if  step in self._detected and \
                        modification_time == self._detected[step].wall_time:
                            continue
                    self._changed.add(step)
                    with open(filepath, "rb") as f:
                        self._detected[step] = FileEvent(
                            wall_time       = modification_time,
                            step            = step,
                            encoded_string  = f.read(),
                            tag             = self.tag,
                            src_name        = filename
                        )

    def get_recent(self):
        self._update_changed_files()
        # retrieve and use only those in the changed set
        recent = sorted([self._detected[step] for step in self._detected], key= lambda e: e.step)
        self._changed.clear()
        return recent
    def _get_values(self):
        self._update_changed_files()
        return sorted([event for event in self._detected.values()], key= lambda e: e.step)
    def get_values(self):
        if self.key_exists:
            print(f"TensorboardStreamableStat ({self.key}) has {len(self._get_values())} values.")
            return self._get_values()
        return []
    
    def clear_values(self):
        # raise NotImplementedError()
        self._detected.clear()
        # raise RuntimeError("TensorboardStreamableStat should only query the EventAccumulator, not update it.")