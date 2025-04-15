from ..base_trader import BaseTrader
from ..utils import TechnicalIndicators, RiskManagement
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import logging

class ScalpingTrader(BaseTrader):
    def __init__(self, symbols, risk_pct=0.01, sl_factor=1.5, tp_factor=1.0,
                 rsi_period=14, rsi_overbought=70, rsi_oversold=30,
                 atr_period=14, atr_threshold=None):
        super().__init__(symbols, risk_pct, sl_factor, tp_factor)
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.atr_period = atr_period
        self.atr_threshold = atr_threshold
        self.indicators = TechnicalIndicators()
        
    def define_strategy(self, symbol):
        """Define scalping strategy logic"""
        try:
            # Get historical data with shorter timeframe for scalping
            data = self.get_hist_data(symbol, n_bars=100, timeframe=mt5.TIMEFRAME_M5)
            if data.empty:
                return None, None, None
            
            # Calculate indicators
            atr = self.indicators.calculate_atr(data['high'], data['low'], data['close'], self.atr_period)
            rsi = self.indicators.calculate_rsi(data['close'], self.rsi_period)
            
            # Calculate signal based on RSI
            if rsi.iloc[-1] < self.rsi_oversold:
                signal = 1  # Buy signal
            elif rsi.iloc[-1] > self.rsi_overbought:
                signal = -1  # Sell signal
            else:
                signal = 0  # No signal
                
            return atr.iloc[-1], signal, rsi.iloc[-1]
            
        except Exception as e:
            logging.error(f"Error in strategy definition for {symbol}: {e}")
            return None, None, None

    def execute_trades(self):
        """Execute trading logic"""
        for symbol in self.symbols:
            # Get strategy signals
            atr, signal, rsi = self.define_strategy(symbol)
            if any(x is None for x in [atr, signal, rsi]):
                logging.warning(f"Skipping {symbol} due to missing strategy data")
                continue

            # Skip if volatility is too low
            if self.atr_threshold and atr < self.atr_threshold:
                logging.info(f"Skipping {symbol} due to low volatility (ATR: {atr:.5f})")
                continue

            # Get current price data
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                continue

            # Check existing positions
            long_positions, short_positions = self.check_positions(symbol)
            
            # Calculate position size based on risk
            lotsize = self.calculate_position_size(symbol, atr)
            
            # Execute trades with tighter stops for scalping
            if signal == 1 and long_positions == 0:
                sl_price = round(tick.ask - (self.sl_factor * atr), 5)
                tp_price = round(tick.ask + (self.tp_factor * atr), 5)
                self.place_order(symbol, mt5.ORDER_TYPE_BUY, sl_price, tp_price, lotsize)
                
            elif signal == -1 and short_positions == 0:
                sl_price = round(tick.bid + (self.sl_factor * atr), 5)
                tp_price = round(tick.bid - (self.tp_factor * atr), 5)
                self.place_order(symbol, mt5.ORDER_TYPE_SELL, sl_price, tp_price, lotsize)
            
            # Log current market state
            logging.info(f'Symbol: {symbol}, Price: {tick.ask}, ATR: {atr:.5f}, RSI: {rsi:.2f}, Signal: {signal}')