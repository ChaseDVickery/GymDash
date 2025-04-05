from src.api.internals.extensions.tensorboard_extensions import patch as patch_tensorboard_extensions

def apply_extension_patches():
    patch_tensorboard_extensions()