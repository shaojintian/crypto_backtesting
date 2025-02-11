import numpy as np
import pandas as pd
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter,Trade
from pandas import DataFrame
import talib.abstract as ta
from technical import qtpylib

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from pandas import DataFrame
from typing import Optional, Union

class VolMeanReversionStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "3m"
    
    # Minimal ROI
    minimal_roi = {
        "0": 0.02,  # 2% profit
        "30": 0.01,
        "60": 0.005
    }

    # Parameters
    bb_window = IntParameter(10, 50, default=20, space='buy')
    bb_std = DecimalParameter(1.5, 3.0, default=2.0, decimals=1, space='buy')
    vol_window = IntParameter(10, 50, default=20, space='buy')
    
    # Stoploss
    stoploss = -0.01  # 2% stoploss
    
    # trailing stoploss
    trailing_stop: bool = True
    trailing_stop_positive: float = 0.01
    trailing_stop_positive_offset: float = 0.0
    trailing_only_offset_is_reached = False
    use_custom_stoploss: bool = True

    can_short = True

    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs,
    ) -> float | None:
        """
        Custom stoploss logic, returning the new distance relative to current_rate (as ratio).
        e.g. returning -0.05 would create a stoploss 5% below current_rate.
        The custom stoploss can never be below self.stoploss, which serves as a hard maximum loss.

        For full documentation please go to https://www.freqtrade.io/en/latest/strategy-advanced/

        When not implemented by a strategy, returns the initial stoploss value.
        Only called when use_custom_stoploss is set to True.

        :param pair: Pair that's currently analyzed
        :param trade: trade object.
        :param current_time: datetime object, containing the current datetime
        :param current_rate: Rate, calculated based on pricing settings in exit_pricing.
        :param current_profit: Current profit (as ratio), calculated based on current_rate.
        :param after_fill: True if the stoploss is called after the order was filled.
        :param **kwargs: Ensure to keep this here so updates to this won't break your strategy.
        :return float: New stoploss value, relative to the current_rate
        """
        return self.stoploss
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Volatility
        dataframe['volatility'] = dataframe['close'].rolling(window=self.vol_window.value).std()
        dataframe['volatility_mean'] = dataframe['volatility'].rolling(window=self.vol_window.value).mean()
        
        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(
            dataframe['close'], 
            window=self.bb_window.value,
            stds=self.bb_std.value
        )
        dataframe['bb_upperband'] = bollinger['upper']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_lowerband'] = bollinger['lower']
        
        # Volume Filters
        dataframe['volume_mean'] = dataframe['volume'].rolling(window=self.vol_window.value).mean()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # Price below lower band
                (dataframe['close'] < dataframe['bb_lowerband']) &
                # High volatility
                (dataframe['volatility'] > dataframe['volatility_mean']) &
                # Good volume
                (dataframe['volume'] > dataframe['volume_mean'])
            ),
            'enter_short'
        ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # Price above middle band
                (dataframe['close'] > dataframe['bb_middleband']) |
                # Volatility back to normal
                (dataframe['volatility'] < dataframe['volatility_mean'])
            ),
            'exit_short'
        ] = 1
        
        return dataframe