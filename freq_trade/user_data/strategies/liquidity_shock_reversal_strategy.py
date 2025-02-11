# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these imports ---
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from pandas import DataFrame
from typing import Optional, Union
logger = logging.getLogger(__name__)
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

class LiquidityShockReversalStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "3m"
    
    stoploss = -0.01
    # Liquidity Parameters
    vol_shock_mult = DecimalParameter(2.0, 5.0, default=3.0, space='buy')
    price_impact = DecimalParameter(0.005, 0.05, default=1e-7, space='buy')
    window_size = IntParameter(3, 10, default=5, space='buy')

    can_short = True

    
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Volume Shock Detection
        dataframe['volume_ma'] = dataframe['volume'].rolling(window=self.window_size.value).mean()
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']
        dataframe['volume_shares'] = dataframe['volume']*dataframe['close']
        
        # Price Impact
        dataframe['returns'] = dataframe['close'].pct_change()
        dataframe['price_impact'] = dataframe['returns'].abs() / (dataframe['volume'] * dataframe['close'])
        #logger.info(dataframe['price_impact'])

        # Liquidity Shock Score
        dataframe['shock_score'] = (
            (dataframe['volume_ratio'] > self.vol_shock_mult.value) & 
            (dataframe['price_impact'] > self.price_impact.value)
        ).astype(int)
        
        # Mean Reversion Signal
        dataframe['future_return'] = dataframe['close'].shift(-4) / dataframe['close'] - 1
        dataframe['reversal_signal'] = (
            (dataframe['shock_score'] == 1) & 
            (dataframe['returns'] < -self.price_impact.value)
        )
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                dataframe['reversal_signal'] &
                (dataframe['volume'] > 0) &
                ( dataframe['volume_shares'] > 100_0000)
            ),
            'enter_short'
        ] = 1
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['future_return'] > self.price_impact.value) |
                (dataframe['volume_ratio'] < 1.0)
            ),
            'exit_short'
        ] = 1
        
        return dataframe