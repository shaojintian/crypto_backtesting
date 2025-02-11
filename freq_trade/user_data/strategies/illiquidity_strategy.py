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


class IlliquidityStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "3m"

    # 0.5%
    stoploss = -0.010

    max_volume_ratio = 0.25  # 25% of volume

    can_short = True
    use_custom_stoploss: bool = False

    trailing_stop: bool = True
    trailing_stop_positive: float | None = 0.03
    trailing_stop_positive_offset: float = 0.0
    trailing_only_offset_is_reached = False

    


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

    amihud_threshold = DecimalParameter(low=0.05, high=0.05, default=0.05, 
        space='buy', optimize=True)
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Add volume and illiquidity indicators"""

        # Calculate rolling volume average
        dataframe['volume_mean'] = dataframe['volume'].rolling(
            window=self.volume_window.value
        ).mean()
        
        # Calculate volume ratio
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_mean']
        dataframe['volume_shares'] = dataframe['volume'] * dataframe['close']

        # Price change percentage
        dataframe['price_pct'] = dataframe['close'].pct_change() * 100
        
        # Calculate Amihud illiquidity ratio (absolute return / volume)
        dataframe['amihud_ratio'] = (dataframe['price_pct'].abs() / dataframe['volume'])
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Entry signals based on Amihud illiquidity ratio and volume pump"""
        
        dataframe.loc[
            (
                # Volume is X times higher than average
                (dataframe['volume_ratio'] > self.volume_multiplier.value) &
                # Amihud illiquidity ratio is higher, indicating higher volatility
                (dataframe['amihud_ratio'] > self.amihud_threshold.value) &
                # Ensure there is enough trading volume
                (dataframe['volume_shares'] > 10_0000) & 
                # Price has increased
                (dataframe['price_pct'] > 0)
            ),
            'enter_long'
        ] = 1
        
        dataframe.loc[
            (
                # Volume is X times higher than average
                (dataframe['volume_ratio'] > self.volume_multiplier.value) &
                # Amihud illiquidity ratio is higher, indicating higher volatility
                (dataframe['amihud_ratio'] > self.amihud_threshold.value) &
                # Ensure there is enough trading volume
                (dataframe['volume_shares'] > 10_0000) & 
                # Price has decreased
                (dataframe['price_pct'] < 0)
            ),
            'enter_short'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit signals when Amihud illiquidity ratio normalizes"""
        
        # Exit long positions when Amihud ratio decreases (liquidity improves)
        dataframe.loc[
            (
                # Amihud ratio decreases, liquidity improves
                (dataframe['amihud_ratio'] < self.amihud_threshold.value/2)
            ),
            'exit_long'
        ] = 1

        # Exit short positions when Amihud ratio decreases (liquidity improves)
        dataframe.loc[
            (
                # Amihud ratio decreases, liquidity improves
                (dataframe['amihud_ratio'] < self.amihud_threshold.value/2)
            ),
            'exit_short'
        ] = 1
        
        return dataframe