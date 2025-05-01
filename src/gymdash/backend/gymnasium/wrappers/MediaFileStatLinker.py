
import logging
from pathlib import Path
from typing import Callable, Union, List, Dict, Iterable, Any
from gymdash.backend.tensorboard.MediaLinkStreamableStat import MediaLinkStreamableStat

import numpy as np

try:
    from gymnasium import Env, logger
    from gymnasium.wrappers import RecordVideo
    _has_gym = True
except ImportError:
    _has_gym = False
    
try:
    from torch.utils.tensorboard import SummaryWriter
    _has_tensorboard = True
except ImportError:
    _has_tensorboard = False
    
try:
    import torch as th
    _has_torch = True
except:
    _has_torch = False
    

if not _has_gym:
    raise ImportError("Install gymnasium to use gymdash environment wrappers.")
if not _has_tensorboard:
    raise ImportError("Install tensorboard to use gymdash environment wrappers.")
if not _has_torch:
    raise ImportError("Install torch to use gymdash environment wrappers.")

logger = logging.getLogger(__name__)

# class MediaFileStatLinker(Streamer):
class MediaFileStatLinker:
    def __init__(self, streamer_name: str, media_link_stats: List[MediaLinkStreamableStat]):
        self._streamer_name = streamer_name
        self.stats = media_link_stats

    def get_stat_keys(self):
        return [(stat.key, stat.tag) for stat in self.stats]
        # return [stat.key for stat in self.stats]
        
    @property
    def streamer_name(self):
        return self._streamer_name

    def Reload(self):
        logger.warning(f"Running Reload on MediaFileStatLinker streamer does nothing.")
        # self.streamer.Reload()

    def _stats_for_tag(self, tag: str):
        return [stat for stat in self.stats if stat.tag == tag]
    def _stat_for_key(self, key: str):
        for stat in self.stats:
            if stat.key == key:
                return stat
        return None
    
    def get_all_from_tag(self, tag: str):
        return {stat.key: stat.get_values() for stat in self._stats_for_tag(tag)}
    
    def get_all_recent(self):
        return {stat.key: stat.get_recent() for stat in self.stats}
    
    def get_recent_from_tag(self, tag: str):
        return {stat.key: stat.get_recent() for stat in self._stats_for_tag(tag)}

    def get_recent_from_key(self, key:str) -> List[Any]:
        stat = self._stat_for_key(key)
        if stat is None:
            return []
        else:
            return stat.get_recent()
    
    def reset_streamer(self):
        for stat in self.stats:
            stat.reset()