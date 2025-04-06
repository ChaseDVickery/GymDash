import src.api.internals.stat_tags as tags
from tensorboard.backend.event_processing.event_accumulator import DEFAULT_SIZE_GUIDANCE, STORE_EVERYTHING_SIZE_GUIDANCE
from typing import Dict, List, Any, Union

from dataclasses import dataclass

CUSTOM_SIZE_GUIDANCE = {
    tags.TB_COMPRESSED_HISTOGRAMS: 500,
    tags.TB_IMAGES: 32,
    tags.TB_AUDIO: 32,
    tags.TB_SCALARS: 10000,
    tags.TB_HISTOGRAMS: 1,
    tags.TB_TENSORS: 10,
}

TB_CONFIG_SIZE_GUIDANCE = STORE_EVERYTHING_SIZE_GUIDANCE

@dataclass
class GDConfig:
    tb_size_guidance: Dict[str, int] = TB_CONFIG_SIZE_GUIDANCE

CONFIG: GDConfig = GDConfig()

def get_config():
    return CONFIG

def set_global_config(args):
    CONFIG = GDConfig()