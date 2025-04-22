import builtins
import pkgutil
import sys
import importlib

_cached_modules = []

# https://stackoverflow.com/questions/56797480/python-get-type-object-from-its-name
def get_type(type_name, module_name=None): 
    """
    Attempts to find and return the input type by name.
    Returns None if type name cannot be found.
    """
    try:
        return getattr(builtins, type_name)
    except AttributeError:
        try:
            obj = globals()[type_name]
        except KeyError:
            # Try again with loaded modules
            # for finder, name, ispkg in pkgutil.walk_packages(path=None, onerror=lambda x: x):
            #     print(name)
            if module_name is not None:
                module = importlib.import_module(module_name)
                try:
                    print(f"found '{type_name}' in '{module_name}'")
                    obj = getattr(module, type_name)
                except KeyError:
                    return None
            else:
                return None
        return obj if isinstance(obj, type) else None