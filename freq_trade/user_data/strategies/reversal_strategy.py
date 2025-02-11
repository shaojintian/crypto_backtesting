# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these imports ---
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from pandas import DataFrame
from typing import Optional, Union

from freqtrade.strategy import (
    IStrategy,
    Trade,
    Order,
    PairLocks,
    informative,  # @informative decorator
    # Hyperopt Parameters
    BooleanParameter,
    CategoricalParameter,
    DecimalParameter,
    IntParameter,
    RealParameter,
    # timeframe helpers
    timeframe_to_minutes,
    timeframe_to_next_date,
    timeframe_to_prev_date,
    # Strategy helper functions
    merge_informative_pair,
    stoploss_from_absolute,
    stoploss_from_open,
)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
from technical import qtpylib

class MeanReversionStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "3m"
    
    # 参数优化范围
    bb_length = IntParameter(10, 50, default=20, space='buy')
    bb_std = DecimalParameter(1.5, 3.0, default=2.0, space='buy')
    rsi_length = IntParameter(10, 30, default=14, space='buy')
    vol_mult = DecimalParameter(1.5, 5.0, default=2.0, space='buy')
    sigma_multiplier = DecimalParameter(4.0, 8.0, default=6.0, space='buy')
    vol_window = IntParameter(20, 100, default=50, space='buy')
    
    # 止损设置
    stoploss = -0.01
    
    # ROI设置
    minimal_roi = {
        "0": 0.02,
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 计算布林带
        bollinger = qtpylib.bollinger_bands(
            dataframe['close'], 
            window=self.bb_length.value,
            stds=self.bb_std.value
        )
        dataframe['bb_upperband'] = bollinger['upper']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_lowerband'] = bollinger['lower']


         # Calculate volatility
        dataframe['std'] = dataframe['close'].rolling(window=self.vol_window.value).std()
        dataframe['upper_risk'] = dataframe['close'].rolling(window=self.vol_window.value).mean() + \
                                 self.sigma_multiplier.value * dataframe['std']
        dataframe['lower_risk'] = dataframe['close'].rolling(window=self.vol_window.value).mean() - \
                                 self.sigma_multiplier.value * dataframe['std']
        
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_length.value)
        
        # 成交量均值
        dataframe['volume_mean'] = dataframe['volume'].rolling(window=20).mean()
        dataframe['volume_std'] = dataframe['volume'].rolling(window=20).std()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # 价格低于下轨
                (dataframe['close'] < dataframe['bb_lowerband']) &
                # RSI超卖
                (dataframe['rsi'] < 30) &
                # 放量
                (dataframe['volume'] > dataframe['volume_mean'] * self.vol_mult.value) &

                # 价格在风险区间内
                (dataframe['close'] > dataframe['lower_risk']) 
            ),
            'enter_long'
        ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # 价格回归均值
                (dataframe['close'] > dataframe['bb_middleband']) |
                # RSI超买
                (dataframe['rsi'] > 70)
            ),
            'exit_long'
        ] = 1
        
        return dataframe