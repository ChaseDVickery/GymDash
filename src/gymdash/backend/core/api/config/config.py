import gymdash.backend.core.api.config.stat_tags as tags

try:
    from tensorboard.backend.event_processing.event_accumulator import (
        DEFAULT_SIZE_GUIDANCE, STORE_EVERYTHING_SIZE_GUIDANCE)
    _has_tensorboard = True
except ImportError:
    _has_tensorboard = False
    
from dataclasses import dataclass, field
from typing import Dict

if _has_tensorboard:
    CUSTOM_SIZE_GUIDANCE = {
        tags.TB_COMPRESSED_HISTOGRAMS: 500,
        tags.TB_IMAGES: 32,
        tags.TB_AUDIO: 32,
        tags.TB_SCALARS: 10000,
        tags.TB_HISTOGRAMS: 1,
        tags.TB_TENSORS: 10,
    }
    TB_CONFIG_SIZE_GUIDANCE = STORE_EVERYTHING_SIZE_GUIDANCE
else:
    CUSTOM_SIZE_GUIDANCE = {
        "distributions": 500,
        "images": 32,
        "audio": 32,
        "scalars": 10000,
        "histograms": 1,
        "tensors": 10,
    }
    TB_CONFIG_SIZE_GUIDANCE = {
        "distributions": 0,
        "images": 0,
        "audio": 0,
        "scalars": 0,
        "histograms": 0,
        "tensors": 0,
    }



@dataclass
class GDConfig:
    tb_size_guidance: Dict[str, int] = field(default_factory=lambda: TB_CONFIG_SIZE_GUIDANCE)

CONFIG: GDConfig = GDConfig()

def set_global_config(args):
    CONFIG = GDConfig()