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
    timeframe = "1m"

    # 0.5%
    stoploss = -0.010

    max_volume_ratio = 0.25  # 25% of volume


    use_custom_stoploss: bool = False
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

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: str | None, side: str,
                 **kwargs) -> float:
        """
        Customize leverage for each new trade. This method is only called in futures mode.

        :param pair: Pair that's currently analyzed
        :param current_time: datetime object, containing the current datetime
        :param current_rate: Rate, calculated based on pricing settings in exit_pricing.
        :param proposed_leverage: A leverage proposed by the bot.
        :param max_leverage: Max leverage allowed on this pair
        :param entry_tag: Optional entry_tag (buy_tag) if provided with the buy signal.
        :param side: "long" or "short" - indicating the direction of the proposed trade
        :return: A leverage amount, which is between 1.0 and max_leverage.
        """
        return 1.0

    
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
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Add volume indicators"""
        
        # Calculate rolling volume average
        dataframe['volume_mean'] = dataframe['volume'].rolling(
            window=self.volume_window.value
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