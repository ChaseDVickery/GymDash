import stable_baselines3 as sb
from stable_baselines3.common.base_class import BaseAlgorithm
from stable_baselines3.common.type_aliases import MaybeCallback
import typing

class SBModelWrapper:
    """
    Wrapper for StableBaselines3 BaseAlgorithm.
    See https://stable-baselines3.readthedocs.io/en/master/modules/base.html
    """
    def __init__(self, algo:BaseAlgorithm) -> None:
        self.algo = algo

    def dump_logs(self):
        return self.algo.dump_logs()

    def get_env(self):
        return self.algo.get_env()

    def get_parameters(self):
        return self.algo.get_parameters()

    def get_vec_normalize_env(self):
        return self.algo.get_vec_normalize_env()
    
    def learn(
        self,
        total_timesteps: int,
        callback: MaybeCallback = None,
        log_interval: int = 100,
        tb_log_name: str = "run",
        reset_num_timesteps: bool = True,
        progress_bar: bool = False
    ):
        return self.algo.learn(
            total_timesteps,
            callback,
            log_interval,
            tb_log_name,
            reset_num_timesteps,
            progress_bar
        )