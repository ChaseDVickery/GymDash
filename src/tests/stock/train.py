# Example training script taken from a post by Zhi Li:
# https://medium.com/datapebbles/building-a-trading-bot-with-deep-reinforcement-learning-drl-b9519a8ba2ac

from .StockTradingEnv import StockTradingEnv
from pybroker import YFinance
import pybroker
pybroker.enable_data_source_cache('yfinance')
import pandas as pd
from stable_baselines3 import PPO
import os
import gymnasium as gym
from gymnasium.wrappers import RecordVideo

from stable_baselines3.common.logger import configure, TensorBoardOutputFormat

# from src.api.internals.callbacks import LogTrainingInfo
from src.api.internals.logging.callbacks import LogTrainingInfoCallback, TensorboardPathCorrectionCallback
from src.api.internals.logging.wrappers.LogTrainingInfoWrapper import LogTrainingInfoWrapper
from src.api.internals.logging.wrappers.TensorboardStreamWrapper import TensorboardStreamWrapper
from src.api.internals.logging.wrappers.RecordVideoToTensorboard import RecordVideoToTensorboard

from src.api.internals.wrapper_utils import WrapperUtils

def train():
    tb_path = os.path.join("tb", "stock", "train")
    yfinance = YFinance()
    df = yfinance.query(['AAPL'], start_date='3/1/2021', end_date='3/1/2022')
    df['date'] = pd.to_datetime(df['date']).dt.date
    env = StockTradingEnv(df, initial_balance=100000, commission_fee=0.0001, slippage_cost=0.005)
    env = LogTrainingInfoWrapper(env, "testout")
    env = TensorboardStreamWrapper(env, tb_path, ["rewards", "rollout/ep_rew_mean"])
    # env = RecordVideoToTensorboard(env, tb_path, lambda x: True)

    logger = configure(tb_path, ["tensorboard"])

    # logging_callback = LogTrainingInfoCallback("")
    tb_correction_callback = TensorboardPathCorrectionCallback()

    model = PPO("MlpPolicy", env, verbose=0, tensorboard_log=tb_path)
    model.set_logger(logger)
    # model.learn(total_timesteps=1_000, progress_bar=True, callback=logging_callback)
    model.learn(total_timesteps=5_000, progress_bar=True, callback=tb_correction_callback)
    model.save("ppo_aapl")


    print(WrapperUtils.get_wrapper_of_type(env, LogTrainingInfoWrapper).episode_logs)

def train_cartpole():
    tb_path = os.path.join("tb", "cartpole", "train")
    env = gym.make("CartPole-v1", render_mode="rgb_array")
    env = LogTrainingInfoWrapper(env, "testout")
    env = TensorboardStreamWrapper(env, tb_path, ["rewards", "rollout/ep_rew_mean", "episode_video"])
    # env = RecordVideo(env, tb_path, lambda x: x%100 == 0, video_length=0, fps=30)
    r_env = RecordVideoToTensorboard(env, tb_path, lambda x: x%100==0, video_length=0, fps=30)
    env = r_env

    logger = configure(tb_path, ["tensorboard"])

    # logging_callback = LogTrainingInfoCallback("")
    tb_correction_callback = TensorboardPathCorrectionCallback()

    model = PPO("MlpPolicy", env, verbose=0, tensorboard_log=tb_path)
    model.set_logger(logger)
    tb_loggers = [t for t in model.logger.output_formats if isinstance(t, TensorBoardOutputFormat)]
    print(tb_loggers)
    r_env.configure_recorder("episode_video", tb_loggers[0].writer)
    # model.learn(total_timesteps=1_000, progress_bar=True, callback=logging_callback)
    model.learn(total_timesteps=50_000, progress_bar=True, callback=tb_correction_callback)
    model.save("ppo_aapl")


    print(WrapperUtils.get_wrapper_of_type(env, LogTrainingInfoWrapper).episode_logs)

if __name__ == "__main__":
    train()