# Example validation script taken from a post by Zhi Li:
# https://medium.com/datapebbles/building-a-trading-bot-with-deep-reinforcement-learning-drl-b9519a8ba2ac

from StockTradingEnv import StockTradingEnv
from pybroker import YFinance
import pandas as pd
from stable_baselines3 import PPO
from gymnasium.wrappers import RecordVideo

yfinance = YFinance()
df = yfinance.query(['AAPL'], start_date='3/1/2022', end_date='3/1/2023')
df['date'] = pd.to_datetime(df['date']).dt.date
env = StockTradingEnv(df, initial_balance=100000, commission_fee=0.0001, slippage_cost=0.005)

model = PPO.load("ppo_aapl", env=env)

vec_env = model.get_env()
obs = vec_env.reset()
for i in range(len(df['adj_close'])):
    action, _state = model.predict(obs)
    obs, reward, done, info = vec_env.step(action)

env.render_all()