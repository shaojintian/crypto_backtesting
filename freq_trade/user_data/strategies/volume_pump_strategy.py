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


class VolumePumpStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "3m"

    # 0.5%
    stoploss = -0.010
    
    # Volume multiplier parameter
    volume_multiplier = IntParameter(
        low=20, high=100, default=50, 
        space='buy', optimize=True
    )
    
    # Window size for volume average
    volume_window = 100
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Add volume indicators"""
        
        # Calculate rolling volume average
        dataframe['volume_mean'] = dataframe['volume'].rolling(
            window=self.volume_window
        ).mean()
        
        # Calculate volume ratio
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_mean']

        # Price change percentage
        dataframe['price_pct'] = dataframe['close'].pct_change() * 100
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Entry signals based on volume pump"""
        dataframe.loc[
            (
                # Volume is X times higher than average
                (dataframe['volume_ratio'] > self.volume_multiplier.value) &
                # Make sure we have enough data
                (dataframe['volume'] > 0) &
                (dataframe['volume_mean'] > 0) & 
                (dataframe['price_pct'] > 0)
            ),
            'enter_long'
        ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit when volume normalizes"""
        dataframe.loc[
            (
                # Volume back to normal
                (dataframe['volume_ratio'] < self.volume_multiplier.value/2)
            ),
            'exit_long'
        ] = 1
        
        return dataframe