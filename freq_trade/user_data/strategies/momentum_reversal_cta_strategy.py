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

class MomentumReversalCTAStrategy (IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "3m"
    
    stoploss = -0.018
    # Liquidity Parameters
    vol_shock_mult = DecimalParameter(2.0, 5.0, default=3.0, space='buy')
    price_impact = DecimalParameter(0.005, 0.05, default=1e-7, space='buy')
    window_size = IntParameter(3, 10, default=5, space='buy')

    can_short = True

    max_volume_ratio = 0.25  # 25% of volume


    # Momentum parameters
    # Volume multiplier parameter
    volume_multiplier = IntParameter(
        low=20, high=100, default=50, 
        space='buy', optimize=True
    )
    
    # Window size for volume average
    volume_window = IntParameter(
        low=50, high=200, default=100, 
        space='buy', optimize=True
    )

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                          proposed_stake: float, min_stake: Optional[float], max_stake: float,
                          entry_tag: Optional[str], side: str, **kwargs) -> float:
        
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        current_candle = dataframe.iloc[-1]
        
        # Calculate volume in USDT
        volume_usdt = current_candle['volume'] * current_candle['close']
        
        # Max stake is 25% of volume
        max_stake_volume = volume_usdt * self.max_volume_ratio
        
        # Return minimum between proposed stake and volume-based stake
        return min(proposed_stake, max_stake_volume)

    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        #1. reversal indicators
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

        #2. volume indicators
        # Volume multiplier parameter
        # Calculate rolling volume average
        dataframe['volume_mean_momentum'] = dataframe['volume'].rolling(
            window=self.volume_window.value
        ).mean()
        
        # Calculate volume ratio
        dataframe['volume_ratio_momentum'] = dataframe['volume'] / dataframe['volume_mean_momentum']


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
        

        """Entry signals based on volume pump"""
        dataframe.loc[
            (
                # Volume is X times higher than average
                (dataframe['volume_ratio_momentum'] > self.volume_multiplier.value) &
                # Make sure we have enough data
                (dataframe['volume'] > 0) &
                (dataframe['volume_mean_momentum'] > 0) & 
                (dataframe['returns'] > 0)&
                (dataframe['volume_shares'] > 100_0000)
            ),
            'enter_long'
        ] = 0
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['future_return'] > self.price_impact.value) |
                (dataframe['volume_ratio'] < 1.0)
            ),
            'exit_short'
        ] = 1

        dataframe.loc[
            (
                # Volume back to normal
                (dataframe['volume_ratio_momentum'] < self.volume_multiplier.value/2)
            ),
            'exit_long'
        ] = 0
        
        return dataframe