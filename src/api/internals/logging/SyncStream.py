from typing import Optional, Union

class SyncStream:
    """
    Responsible for handling data from a single file.
    Keeps track of the last "consumed" index of data.
    Keeps an internal cache read data.
    Flushes new data back to the log file.
    """
    def __init__(
        self,
        filename: str = "",
        header: Optional[dict[str, Union[float, str]]] = None,
        extra_keys: tuple[str, ...] = (),
        override_existing: bool = True,
    ):
        pass