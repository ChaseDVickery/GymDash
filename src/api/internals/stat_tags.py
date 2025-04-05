
from tensorboard.backend.event_processing import tag_types

ANY_TAG = "any"
TB_TENSORS                  = tag_types.TENSORS
TB_RUN_METADATA             = tag_types.RUN_METADATA
TB_COMPRESSED_HISTOGRAMS    = tag_types.COMPRESSED_HISTOGRAMS
TB_HISTOGRAMS               = tag_types.HISTOGRAMS
TB_IMAGES                   = tag_types.IMAGES
TB_AUDIO                    = tag_types.AUDIO
TB_SCALARS                  = tag_types.SCALARS

TENSORBOARD_TAG_SET = set((
    TB_TENSORS,
    # tag_types.GRAPH,          This is a bool
    # tag_types.META_GRAPH,     This is a bool
    TB_RUN_METADATA,
    TB_COMPRESSED_HISTOGRAMS,
    TB_HISTOGRAMS,
    TB_IMAGES,
    TB_AUDIO,
    TB_SCALARS,
))

EVERY_TAG_SET = set((
    ANY_TAG,
)).union(
    TENSORBOARD_TAG_SET
)