from typing import Any

class StreamerRegistry:
    # Static mapper to track tb streamers
    log_map = {}
    @staticmethod
    def get_streamer(tb_log: str):
        return StreamerRegistry.log_map[tb_log] if tb_log in StreamerRegistry.log_map else None
    @staticmethod
    def register(tb_log: str, streamer: Any):
        if (tb_log in StreamerRegistry.log_map):
            return False
        StreamerRegistry.log_map[tb_log] = streamer
        print(f"Register streamer '{tb_log}'")
        return True