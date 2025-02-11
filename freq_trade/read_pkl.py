import pickle
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

def load_backtest_data(filename: str):
    """从pickle文件加载回测结果"""
    try:
        filepath = Path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"文件不存在: {filename}")
            
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        return data
        
    except FileNotFoundError as e:
        print(f"错误: {e}")
    except pickle.UnpicklingError:
        print(f"错误: 无法解析pickle文件 {filename}")
    except Exception as e:
        print(f"未知错误: {e}")
    return None


if __name__ == "__main__":
    # Load backtest results
    backtest_results = load_backtest_data('user_data/hyperopt_results/hyperopt_tickerdata.pkl')

    # Convert the results to a pandas DataFrame
    print(backtest_results)