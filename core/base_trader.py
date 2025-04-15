import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from abc import ABC, abstractmethod

class BaseTrader(ABC):
    def __init__(self, symbols, risk_pct=0.01, sl_factor=1.5, tp_factor=2.0):
        self.symbols = symbols
        self.risk_pct = risk_pct
        self.sl_factor = sl_factor
        self.tp_factor = tp_factor
        self.initialize_logging()

    def initialize_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def initialize_mt5(self, path, login, server, password):
        """Initialize MT5 connection"""
        if not mt5.initialize(path=path, login=login, server=server, password=password):
            logging.error(f'MT5 initialization failed, error code={mt5.last_error()}')
            raise ConnectionError("MetaTrader5 initialization failed")
        logging.info("MT5 connection initialized successfully")

    def get_hist_data(self, symbol, n_bars, timeframe=mt5.TIMEFRAME_M15):
        """Get historical data for a symbol"""
        try:
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n_bars)
            data = pd.DataFrame(rates)
            data['time'] = pd.to_datetime(data['time'], unit='s')
            data.set_index('time', inplace=True)
            return data
        except Exception as e:
            logging.error(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()

    def place_order(self, symbol, order_type, sl_price, tp_price, lotsize, deviation=20):
        """Place a trading order"""
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            logging.error(f"Failed to fetch tick data for {symbol}")
            return False

        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lotsize,
            "type": order_type,
            "price": price,
            "sl": sl_price,
            "tp": tp_price,
            "deviation": deviation,
            "magic": 199308,
            "comment": "python script open",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logging.error(f'Order placement failed for {symbol}, retcode: {result.retcode if result else "None"}')
            return False
        logging.info(f'Order placed successfully: {result}')
        return True

    def check_positions(self, symbol):
        """Check current positions for a symbol"""
        positions = mt5.positions_get(symbol=symbol)
        if positions is None:
            return 0, 0
        long_positions = sum(pos.type == mt5.ORDER_TYPE_BUY for pos in positions)
        short_positions = sum(pos.type == mt5.ORDER_TYPE_SELL for pos in positions)
        return long_positions, short_positions

    @abstractmethod
    def define_strategy(self, symbol):
        """Strategy-specific logic to be implemented by subclasses"""
        pass

    @abstractmethod
    def execute_trades(self):
        """Trade execution logic to be implemented by subclasses"""
        pass

    def calculate_position_size(self, symbol, atr):
        """Calculate position size based on risk"""
        account_info = mt5.account_info()
        if not account_info:
            logging.error("Failed to get account info")
            return 0.1  # Default minimum lot size
            
        equity = account_info.equity
        risk_amount = equity * self.risk_pct
        
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return 0.1
            
        pip_value = mt5.symbol_info(symbol).point
        risk_pips = atr * self.sl_factor
        
        if risk_pips == 0:
            return 0.1
            
        position_size = risk_amount / (risk_pips / pip_value)
        return round(position_size, 2)