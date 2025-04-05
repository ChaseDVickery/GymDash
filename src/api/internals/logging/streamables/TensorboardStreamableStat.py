from .StreamableStat import StreamableStat
from tensorboard.backend.event_processing import event_accumulator, tag_types
from typing import Set
from src.api.internals.stat_tags import ANY_TAG, TENSORBOARD_TAG_SET

class TensorboardStreamableStat(StreamableStat):
    """
    Class represents an easily appendable stat.
    This specializes in appending new information and
    tracking the last accessed datapoint to minimize
    data transactions when accessing newly-acquired data.
    """
    def __init__(self, accumulator: event_accumulator.EventAccumulator, key: str, tags: Set[str]=set(ANY_TAG)):
        super().__init__()
        if not accumulator:
            raise ValueError("TensorboardStreamableStat was not initialized with a proper EventAccumulator")
        self.ea             = accumulator
        self.key            = key
        self._key_exists    = False
        self.tags           = tags
        self._cached_key_tag= None
        self.associated_tags = set()
        self._cached_data_access_method = None
        # if key not in self.ea.Tags(tag_types.SCALARS):
        #     raise KeyError(f"TensorboardStreamableStat, key '{key}' was not found in the EventAccumulator")

    @property
    def found_key_tag(self):
        if not self.key_exists:
            return None
        return self._cached_key_tag

    @property
    def key_exists(self):
        if not self._key_exists:
            print(f"TensorboardStreamableStat looking for unfound key '{self.key}'")
            # If we can have any tag, then look through every valid tensorboard tag
            # If key found within ANY tag category, use it
            if ANY_TAG in self.tags:
                for tag in TENSORBOARD_TAG_SET:
                    if self.key in self.ea.Tags()[tag]:
                        self._finalize_found_key(tag)
                        break
            else:
                for tag in self.tags:
                    if tag in self.ea.Tags() and self.key in self.ea.Tags()[tag]:
                        self._finalize_found_key(tag)
                        break
            for tag in self.tags:
                if tag in self.ea.Tags() and self.key in self.ea.Tags()[tag]:
                    self.associated_tags.add(tag)
        return self._key_exists
    
    def _finalize_found_key(self, tag):
        self._key_exists = True
        self._cached_key_tag = tag
        print(f"TensorboardStreamableStat finalizing key={self.key} tag={self._cached_key_tag}")
        if tag == tag_types.TENSORS:
            self._cached_data_access_method = self.ea.Tensors
        elif tag == tag_types.GRAPH:
            self._cached_data_access_method = self.ea.Graph
        elif tag == tag_types.META_GRAPH:
            self._cached_data_access_method = self.ea.MetaGraph
        elif tag == tag_types.RUN_METADATA:
            self._cached_data_access_method = self.ea.RunMetadata
        elif tag == tag_types.COMPRESSED_HISTOGRAMS:
            self._cached_data_access_method = self.ea.CompressedHistograms
        elif tag == tag_types.HISTOGRAMS:
            self._cached_data_access_method = self.ea.Histograms
        elif tag == tag_types.IMAGES:
            self._cached_data_access_method = self.ea.Images
        elif tag == tag_types.AUDIO:
            self._cached_data_access_method = self.ea.Audio
        elif tag == tag_types.SCALARS:
            self._cached_data_access_method = self.ea.Scalars
        else:
            raise RuntimeError(f"The key '{self.key}' was found in the EventAccumulator under tag {tag}, but this tag is not associated with any EventAccumulator retrieval method.")

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
        # return self.ea.Scalars(self.key)
        return self._cached_data_access_method(self.key)
    def get_values(self):
        self.ea.Reload()
        if self.key_exists:
            print(f"TensorboardStreamableStat has {len(self._get_values())} values.")
            return self._get_values()
        return []
    
    def clear_values(self):
        pass
        # raise RuntimeError("TensorboardStreamableStat should only query the EventAccumulator, not update it.")