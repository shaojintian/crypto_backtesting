import numpy as np
import pandas as pd
import talib as ta
import matplotlib.pyplot as plt
from scipy.stats import pearsonr

def read_data(filepath: str) -> pd.DataFrame:
    """读取行情数据"""
    return pd.read_csv(filepath, index_col=0)

def calculate_bbands(z: pd.Series, period: int = 100) -> pd.Series:
    """计算布林带因子"""
    up, mid, low = ta.BBANDS(z, period)
    return (up - z) / (up - low)

def norm(x:pd.Series,window:int=2000) -> pd.Series:
    '''滚动标准化
    ---------------------------------------------------------------------
    Params:
    x:因子值或者收益率
    window:滚动标准化的窗口
    ---------------------------------------------------------------------'''
    # 和talib的talib.STDDEV比较，talib中的标准差计算方式是自由度n
    # 而rolling的计算方式是自由度n-1
    factors_rolling_mean = x.rolling(window).mean() # 计算滚动均值，中心化
    factors_rolling_std = x.rolling(window).std() # 计算滚动标准差，缩放
    return (x-factors_rolling_mean)/factors_rolling_std


def rolling_ic_ndarry(x,y):
    '''x、y是ndarray数组'''
    return ta.CORREL(x,y,10)
def rolling_ic_pdseries(x,y):
    '''x、y是pdseries'''
    return x.rolling(10).corr(y)

def clip_factor(x: pd.Series, lower: float = -3, upper: float = 3) -> pd.Series:
    """对因子进行clip截断处理"""
    return x.clip(lower, upper)

def calculate_returns(z: pd.Series) -> pd.Series:
    """计算收益率"""
    return z.shift(-1) / z - 1

def calculate_net_values(pos: np.array, ret: np.array, fee: float = 0) -> np.array:
    """计算净值序列"""
    position_changes = np.hstack((pos[0], np.diff(pos)))
    net_values = 1 + (pos * ret - np.abs(position_changes * fee)).cumsum()
    return net_values


def permutation_test(x, y, n_permutations=100) -> float:
    """执行置换检验以评估x和y之间的关系是否显著。
    -----------------------------------------
    Params:
    x (ndarray): original factor Series
    y (ndarray): Future return series
    n_permutations (int): numbers of permutation
    -----------------------------------------
    Return:
    p_value (float): p_value,the smaller,the better
    -----------------------------------------"""

    original_corr = pearsonr(x, y)[0]  # 计算原始数据的相关系数

    permuted_x = np.empty((n_permutations, len(x)))  # 创建所有置换的矩阵
    for i in range(n_permutations):
        permuted_x[i] = np.random.permutation(x)

    # 计算所有置换的相关系数
    permuted_corrs = np.array([pearsonr(permuted_x[i], y)[0] for i in range(n_permutations)])
    p_value = np.mean(np.abs(permuted_corrs) >= np.abs(original_corr))  # 我们期待p值越小越好
    return p_value

# %%
# ic和sharp : information coefficient and sharp ratio
def cal_ic(x,y):
    '''计算ic'''
    return np.corrcoef(x,y)[0,1]
def cal_sharp(x,y):
    '''计算Sharp,x为仓位,y为未来一个周期收益率'''
    trading_days = 252
    net_values = 1+(x*y).cumsum()
    returns = (net_values[1:]-net_values[:-1])/net_values[:-1]
    ret_mean = returns.mean()
    ret_std = returns.std()
    risk_free = 0.03
    sharp = (ret_mean*trading_days-risk_free)/ret_std*np.sqrt(trading_days)
    return sharp


def plot_histogram(data: pd.Series, title: str):
    """绘制直方图"""
    data.hist(bins=100)
    plt.title(title)
    plt.show()

def main():
    # 读取数据
    z = read_data('510050.SH_15.csv')

    # 计算布林带因子
    x = calculate_bbands(z['close'])

    # 查看标准化之前因子的分布状况
    plot_histogram(x, 'Before Normalization')

    # 对因子进行滚动标准化
    norm_x = norm(x)

    # 查看标准化之后因子的分布状况
    plot_histogram(norm_x, 'After Normalization')

    # 对因子进行clip截断处理
    norm_x = clip_factor(norm_x)

    # 查看截断之后因子的分布状况
    plot_histogram(norm_x, 'After Clipping')

    # 计算收益率
    ret = calculate_returns(z['close'])

    # 查看收益率的分布情况
    print(ret.describe())
    plot_histogram(ret, 'Returns Distribution')

    # 计算净值
    pos = np.array(norm_x)
    ret = np.array(ret)
    net_value = calculate_net_values(pos, ret)

    # 绘制净值曲线
    pd.Series(net_value).plot(title='Net Value')
    plt.show()

    # 查看仓位的分布
    plot_histogram(pd.Series(pos), 'Position Distribution')

    # 查看收益率的分布
    plot_histogram(pd.Series(ret), 'Returns Distribution')

    # 计算夏普比率
    sharpe_ratio = cal_sharp(pd.Series(ret), pd.Series(pos))
    print(f'Sharpe Ratio: {sharpe_ratio}')

if __name__ == '__main__':
    main()