import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Optional, Tuple, Union
import logging

class TechnicalIndicators:
    @staticmethod
    def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        return ta.atr(high=high, low=low, close=close, length=length)
    
    @staticmethod
    def calculate_zscore(series: pd.Series, window: int = 20) -> pd.Series:
        """Calculate Z-Score of a series"""
        return (series - series.rolling(window=window).mean()) / series.rolling(window=window).std()
    
    @staticmethod
    def calculate_ma(close: pd.Series, length: int = 20, type: str = 'ema') -> pd.Series:
        """Calculate Moving Average (EMA or SMA)"""
        if type.lower() == 'ema':
            return ta.ema(close=close, length=length)
        return ta.sma(close=close, length=length)

    @staticmethod
    def calculate_bollinger_bands(close: pd.Series, length: int = 20, std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        indicator = ta.bbands(close=close, length=length, std=std)
        return indicator['BBL_20_2.0'], indicator['BBM_20_2.0'], indicator['BBU_20_2.0']
    
    @staticmethod
    def calculate_rsi(close: pd.Series, length: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        return ta.rsi(close=close, length=length)

    @staticmethod
    def calculate_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD"""
        indicator = ta.macd(close=close, fast=fast, slow=slow, signal=signal)
        return indicator['MACD_12_26_9'], indicator['MACDs_12_26_9'], indicator['MACDh_12_26_9']

class RiskManagement:
    @staticmethod
    def calculate_position_size(account_equity: float, risk_pct: float, entry_price: float, 
                              stop_loss: float, pip_value: float = 1.0) -> float:
        """
        Calculate position size based on risk parameters
        :param account_equity: Account balance
        :param risk_pct: Risk percentage per trade (decimal)
        :param entry_price: Entry price
        :param stop_loss: Stop loss price
        :param pip_value: Value of one pip in account currency
        :return: Position size
        """
        if stop_loss == 0 or entry_price == 0:
            return 0.1  # Minimum lot size
            
        risk_amount = account_equity * risk_pct
        stop_distance = abs(entry_price - stop_loss)
        
        if stop_distance == 0:
            return 0.1
            
        position_size = risk_amount / (stop_distance * pip_value)
        return round(position_size, 2)

    @staticmethod
    def calculate_risk_reward(entry_price: float, stop_loss: float, take_profit: float) -> float:
        """Calculate risk to reward ratio"""
        if stop_loss == 0 or entry_price == 0:
            return 0
            
        risk = abs(entry_price - stop_loss)
        if risk == 0:
            return 0
            
        reward = abs(take_profit - entry_price)
        return reward / risk