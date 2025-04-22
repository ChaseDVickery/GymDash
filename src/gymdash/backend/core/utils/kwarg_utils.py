from typing import Dict, Any


def overwrite_new_kwargs(old_kwargs, *args) -> Dict[str, Any]:
        """
        Returns a unified dictionary of keyword arguments where each subsequent
        keyword dictionary adds its own values to the old dictionary,
        overwriting existing values at matching keys.

        Args:
            old_kwargs: Old dict of keyword arguments to override.
            *args: Tuple of new keyword arguments to apply to the old.
        Return:
            new_kwargs: New dictionary containing unified kwargs
        """
        new_kwargs = {}
        for k, v in old_kwargs.items():
            new_kwargs[k] = v
        for kwarg_dict in args:
            for key, value in kwarg_dict.items():
                new_kwargs[key] = value
        return new_kwargs