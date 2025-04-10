try:
    from tensorboard.backend.event_processing import tag_types
    _has_tensorboard = True
except ImportError:
    _has_tensorboard = False
    

print(_has_tensorboard)
ANY_TAG = "any"
if _has_tensorboard:
    TB_TENSORS                  = tag_types.TENSORS
    TB_RUN_METADATA             = tag_types.RUN_METADATA
    TB_COMPRESSED_HISTOGRAMS    = tag_types.COMPRESSED_HISTOGRAMS
    TB_HISTOGRAMS               = tag_types.HISTOGRAMS
    TB_IMAGES                   = tag_types.IMAGES
    TB_AUDIO                    = tag_types.AUDIO
    TB_SCALARS                  = tag_types.SCALARS
else:
    TB_TENSORS                  ="tensors"
    TB_RUN_METADATA             ="run_metadata"
    TB_COMPRESSED_HISTOGRAMS    ="distributions"
    TB_HISTOGRAMS               ="histograms"
    TB_IMAGES                   ="images"
    TB_AUDIO                    ="audio"
    TB_SCALARS                  ="scalars"

TENSORBOARD_TAG_SET = set((
    TB_TENSORS,
    TB_RUN_METADATA,
    TB_COMPRESSED_HISTOGRAMS,
    TB_HISTOGRAMS,
    TB_IMAGES,
    TB_AUDIO,
    TB_SCALARS,
))

MEDIA_TAG_SET = set((
    TB_IMAGES,
    TB_AUDIO,
))

EVERY_TAG_SET = set((
    ANY_TAG,
)).union(
    TENSORBOARD_TAG_SET
)