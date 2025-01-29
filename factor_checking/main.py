import pandas as pd
import numpy as np

'''
1.因子值做标准化(归一化)、截取极值后得到仓位(可以截取-3到3、-2到2等,分别代表3倍、2倍杠杆)
2.仓位与未来1个周期的收益率计算,得到净值序列,计算过程需要考虑仓位变动的磨损
3.得到净值序列后,可以根据净值序列计算夏普、calmar等等业绩统计指标
'''

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


def cal_sharp(ret:pd.Series,pos:pd.Series) -> float:
    '''计算夏普比率,risk free rate为无风险年化收益率,trading days是1年总的交易日
    -------------------------------------------------------------------------
    Params:
    ret: 未来一个周期的收益率
    pos: 仓位，也就是因子值
    -------------------------------------------------------------------------'''
    rf = 0.03  # 无风险利率
    N = 252  # 一年总的交易日
    
    factor_ret = ret*pos  # 计算因子的收益率
    sharpe = (factor_ret.mean()*np.sqrt(N*16)-rf/(N*16))/factor_ret.std()
    return sharpe
    


    

