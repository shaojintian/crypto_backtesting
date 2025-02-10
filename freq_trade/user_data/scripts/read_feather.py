import pandas as pd
import pyarrow.feather as feather
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def read_feather_data(file_path: str) -> pd.DataFrame:
    """Read and process feather file for FreqTrade"""
    try:
        # Read feather file
        df = pd.read_feather(file_path)
        
        # # Verify required columns
        # required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        # if not all(col in df.columns for col in required_cols):
        #     raise ValueError(f"Missing required columns. Found: {df.columns}")
            
        # # Set index if needed
        # if 'Date' in df.columns:
        #     df.set_index('Date', inplace=True)
        
        # # Ensure datetime index
        # df.index = pd.to_datetime(df.index)
        
        # # Sort by index
        # df.sort_index(inplace=True)
        
        logger.info(f"Successfully loaded {len(df)} rows from {file_path}")
        return df
        
    except Exception as e:
        logger.error(f"Error reading feather file: {e}")
        raise

if __name__ == "__main__":
    # Example usage
    data_dir = Path("/Users/shaoenzo/Documents/GitHub/crypto_backtesting/freq_trade/user_data/data/binance/futures")
    feather_file = data_dir / "BTC_USDT_USDT-3m-futures.feather"
    
    df = read_feather_data(str(feather_file))
    print(df.head())
    print(f"\nDataframe shape: {df.shape}")