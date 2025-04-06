from typing import Any

class StreamerRegistry:
    # Static mapper to track tb streamers
    log_map = {}
    @staticmethod
    def get_streamer(tb_log: str):
        return StreamerRegistry.log_map[tb_log] if tb_log in StreamerRegistry.log_map else None
    @staticmethod
    def _get_or_register(tb_log: str, streamer: Any):
        retrieved = StreamerRegistry.get_streamer(tb_log)
        if retrieved:
            print(f"Got existing streamer from '{tb_log}'")
            return retrieved
        else:
            if StreamerRegistry.register(tb_log, streamer):
                print(f"Registered new streamer to '{tb_log}'")
                return streamer
            else:
                raise ValueError(f"No existing streamer with name '{tb_log}' found, but unable to register")
    @staticmethod
    def get_or_register(streamer: Any):
        return StreamerRegistry._get_or_register(streamer.streamer_name, streamer)
    @staticmethod
    def register(tb_log: str, streamer: Any):
        if (tb_log in StreamerRegistry.log_map):
            return False
        StreamerRegistry.log_map[tb_log] = streamer
        print(f"Register streamer '{tb_log}'")
        return True
    @staticmethod
    def items():
        return StreamerRegistry.log_map.items()
    @staticmethod
    def streamers():
        return StreamerRegistry.log_map.values()