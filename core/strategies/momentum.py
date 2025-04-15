from ..base_trader import BaseTrader
from ..utils import TechnicalIndicators, RiskManagement
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import logging

class MomentumTrader(BaseTrader):
    def __init__(self, symbols, risk_pct=0.01, sl_factor=1.5, tp_factor=2.0,
                 fast_ma=20, slow_ma=50, atr_period=14):
        super().__init__(symbols, risk_pct, sl_factor, tp_factor)
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma
        self.atr_period = atr_period
        self.indicators = TechnicalIndicators()
        
    def define_strategy(self, symbol):
        """Define momentum strategy logic"""
        try:
            # Get historical data
            data = self.get_hist_data(symbol, n_bars=100)
            if data.empty:
                return None, None, None, None
            
            # Calculate indicators
            atr = self.indicators.calculate_atr(data['high'], data['low'], data['close'], self.atr_period)
            fast_ma = self.indicators.calculate_ma(data['close'], self.fast_ma)
            slow_ma = self.indicators.calculate_ma(data['close'], self.slow_ma)
            
            # Calculate trend signal
            trend = 1 if fast_ma.iloc[-1] > slow_ma.iloc[-1] else -1 if fast_ma.iloc[-1] < slow_ma.iloc[-1] else 0
            
            return atr.iloc[-1], trend, fast_ma.iloc[-1], slow_ma.iloc[-1]
            
        except Exception as e:
            logging.error(f"Error in strategy definition for {symbol}: {e}")
            return None, None, None, None

    def execute_trades(self):
        """Execute trading logic"""
        for symbol in self.symbols:
            # Get strategy signals
            atr, trend, fast_ma, slow_ma = self.define_strategy(symbol)
            if any(x is None for x in [atr, trend, fast_ma, slow_ma]):
                logging.warning(f"Skipping {symbol} due to missing strategy data")
                continue

            # Get current price data
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                continue

            # Check existing positions
            long_positions, short_positions = self.check_positions(symbol)
            
            # Calculate position size based on risk
            lotsize = self.calculate_position_size(symbol, atr)
            
            # Trading logic - only trade in trend direction
            if trend == 1 and long_positions == 0:
                sl_price = round(tick.ask - (self.sl_factor * atr), 5)
                tp_price = round(tick.ask + (self.tp_factor * atr), 5)
                self.place_order(symbol, mt5.ORDER_TYPE_BUY, sl_price, tp_price, lotsize)
                
            elif trend == -1 and short_positions == 0:
                sl_price = round(tick.bid + (self.sl_factor * atr), 5)
                tp_price = round(tick.bid - (self.tp_factor * atr), 5)
                self.place_order(symbol, mt5.ORDER_TYPE_SELL, sl_price, tp_price, lotsize)
            
            # Log current market state
            logging.info(f'Symbol: {symbol}, Price: {tick.ask}, ATR: {atr:.5f}, Trend: {trend}, Fast MA: {fast_ma:.5f}, Slow MA: {slow_ma:.5f}')