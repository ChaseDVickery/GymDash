import numpy as np
from typing import List, Dict
from collections.abc import Callable
from .StatLog import StatLog
from stable_baselines3.common.callbacks import BaseCallback
from src.api.internals.wrapper_utils import WrapperUtils
from src.api.internals.logging.wrappers.TensorboardStreamWrapper import TensorboardStreamWrapper

# https://stable-baselines.readthedocs.io/en/master/guide/callbacks.html
class LogTrainingInfoCallback(BaseCallback):
    def __init__(self, log_dir: str, verbose: int = 0):
        super().__init__(verbose)
        self.log_dir = log_dir
        self.episode_logs:  Dict[str, StatLog]  = {}
        self.step_logs:     Dict[str, StatLog]  = {}
        # self.episode_rewards: List[StatLog] = []

        # Those variables will be accessible in the callback
        # (they are defined in the base class)
        # The RL model
        # self.model = None  # type: BaseRLModel
        # An alias for self.model.get_env(), the environment used for training
        # self.training_env = None  # type: Union[gym.Env, VecEnv, None]
        # Number of time the callback was called
        # self.n_calls = 0  # type: int
        # self.num_timesteps = 0  # type: int
        # local and global variables
        # self.locals = None  # type: Dict[str, Any]
        # self.globals = None  # type: Dict[str, Any]
        # The logger object, used to report things in the terminal
        # self.logger = None  # type: logger.Logger
        # # Sometimes, for event callback, it is useful
        # # to have access to the parent object
        # self.parent = None  # type: Optional[BaseCallback]

    def retrieve_new_values(self):
        return 

    def _on_training_start(self) -> None:
        """
        This method is called before the first rollout starts.
        """
        pass

    def _on_rollout_start(self) -> None:
        """
        A rollout is the collection of environment interaction
        using the current policy.
        This event is triggered before collecting new samples.
        """
        pass

    def _on_step(self) -> bool:
        """
        This method will be called by the model after each call to `env.step()`.

        For child callback (of an `EventCallback`), this will be called
        when the event is triggered.

        :return: (bool) If the callback returns False, training is aborted early.
        """
        # print(self.locals)
        dones = self.locals.get("dones")
        # Extract episodic information
        finished_episode = dones is not None and np.any(dones)
        if (finished_episode):
            self._extract_episode_info("rewards", lambda x: x.item(), 0)
            print(self.episode_logs)
            exit()
        # Extract step information
        self._extract_step_info("rewards", lambda x: x.item(), 0)
        print(self.locals)
        print(self.locals["env"].rewards)
        # print(self.step_logs)
        return True

    def _on_rollout_end(self) -> None:
        """
        This event is triggered before updating the policy.
        """
        pass

    def _on_training_end(self) -> None:
        """
        This event is triggered before exiting the `learn()` method.
        """
        pass


    def _extract_step_info(self, key:str, value_transform:Callable=None, default_value=None):
        self._extract_info(self.step_logs, key, value_transform, default_value)
    def _extract_episode_info(self, key:str, value_transform:Callable=None, default_value=None):
        self._extract_info(self.episode_logs, key, value_transform, default_value)

    def _extract_info(self, infos:Dict[str, StatLog], key:str, value_transform:Callable=None, default_value=None):
        if (key not in infos):
            infos[key] = StatLog()
        found, extracted_value = self._try_extract_info(key, value_transform, default_value)
        if (found):
            infos[key].append(extracted_value)

    def _try_extract_info(self, key:str, value_transform:Callable=None, default_value=None):
        value = self.locals.get(key)
        if (value is not None):
            return True, value_transform(value) if value_transform is not None else value
        else:
            return False, default_value

    # def _try_extract_info(self, stat_log:StatLog, key:str, value_transform:Callable=None, default_value=None):
    #     value = self.locals.get(key)
    #     if (value is not None):
    #         stat_log.append(value_transform(value) if value_transform is not None else value)
    #         return True
    #     else:
    #         if (default_value is not None):
    #             stat_log.append(default_value)
    #         return False
    

class TensorboardPathCorrectionCallback(BaseCallback):
    def __init__(self, verbose: int = 0):
        super().__init__(verbose)

    def _on_step(self) -> bool:
        return super()._on_step()

    def _on_training_start(self) -> None:
        """
        This method is called before the first rollout starts.
        """
        if (self.model):
            tb_log_wrapper = WrapperUtils.get_wrapper_of_type(self.model.env, TensorboardStreamWrapper)
            if tb_log_wrapper:
                print(f"Setting wrapper log path to '{self.model.logger.get_dir()}'")
                tb_log_wrapper.set_log_path(self.model.logger.get_dir())