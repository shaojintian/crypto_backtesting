"""Data and utilities for testing."""

from __future__ import annotations

import pandas as pd
import polars as pl


def _read_file(filename):
    from os.path import dirname, join

    return pd.read_csv(join(dirname(__file__), filename),
                       index_col=0, parse_dates=True)

def _read_file_ms_timeformat(filename):
    from os.path import dirname, join, basename, splitext

    # Get clean symbol name from filename
    symbol = splitext(basename(filename))[0].split('-')[0]
    
    # Read data
    df = pl.read_csv(join(dirname(__file__), filename))
    df = (df.with_columns([
            pl.col('Open_time')
              .cast(pl.Int64)
              .cast(pl.Datetime(time_unit='ms'))
              .alias('Date')
        ]))
    
    # Return dict with symbol as key
    return {symbol: df.to_pandas().set_index('Date')}

GOOG = _read_file('GOOG.csv')
"""DataFrame of daily NASDAQ:GOOG (Google/Alphabet) stock price data from 2004 to 2013."""

EURUSD = _read_file('EURUSD.csv')
"""DataFrame of hourly EUR/USD forex data from April 2017 to February 2018."""

_1INCHUSD = _read_file_ms_timeformat('1INCHUSDT-3m-2024-11.csv')
_1000cheems = _read_file_ms_timeformat('1000CHEEMSUSDT-3m-2024-11.csv')

def SMA(arr: pd.Series, n: int) -> pd.Series:
    """
    Returns `n`-period simple moving average of array `arr`.
    """
    return pd.Series(arr).rolling(n).mean()
