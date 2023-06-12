import MetaTrader5 as mt5
from datetime import datetime
import pandas as pd
import numpy as np
from functools import reduce
import talib
import time
from time import sleep
import logging
from dotenv import load_dotenv
import os

load_dotenv()
# Load environment variables
mt_login_id = int(os.getenv("mt_login_id"))
mt_password = os.getenv("mt_password")
mt_server_name = os.getenv("mt_server_name")

if not mt_login_id or not mt_password or not mt_server_name:
    raise ValueError("Please set the environment variables METATRADER_LOGIN_ID, METATRADER_PASSWORD and METATRADER_SERVER")

class MysteryOfTheMissingHeart:
    sl_factor = 3
    tp_factor = 1
    upper_threshold = 1
    lower_threshold = 0
    #exit_threshold = 0.01

    def __init__(self, symbol, lot_size):
        self.symbol = symbol
        self.lot = lot_size
        self.order_result_comment = None
        self.pos_summary = None
        self.Invested = None
        if not mt5.initialize(login=mt_login_id, server=mt_server_name, password=mt_password):
            print("initialize() failed, error code =",mt5.last_error())
            quit()
        if self.check_symbol(self.symbol):
            print(f"Symbol {self.symbol} is in the Market Watch.")
        if self.check_symbol('DX.f'):
            print("Symbol USDx is in the Market Watch.")
            
    def check_symbol(self, symbol):
        """Checks if a symbol is in the Market Watch. If it's not, the symbol is added."""
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name,password=mt_password)
        symbols = mt5.symbols_get()
        symbol_list = [s.name for s in symbols]
        if symbol not in symbol_list:
            print("Symbol {} not found in Market Watch. Adding it...".format(symbol))
            if not mt5.symbol_select(symbol, True):
                print("Failed to add {} to Market Watch".format(symbol))
                return False
        return True

    def get_hist_data(self, symbol, n_bars, timeframe=mt5.TIMEFRAME_H1): #changed timeframe
        """ Function to import the data of the chosen symbol"""
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name,password=mt_password)
        #get data and convert it into pandas dataframe
        utc_from = datetime.now()
        rates = mt5.copy_rates_from(symbol, timeframe, utc_from, n_bars)
        data = pd.DataFrame(rates)
        data['time'] = pd.to_datetime(data['time'], unit='s')
        data['time'] = pd.to_datetime(data['time'], format='%Y-%m-%d')
        data = data.set_index('time')
        return data

    def place_order(self, order_type, sl_price, tp_price):
        # point = mt5.symbol_info(self.symbol).point
        price = mt5.symbol_info_tick(self.symbol).last
        deviation = 20
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": self.lot,
            "type": order_type,
            "price": price,
            "sl": sl_price,
            "tp": tp_price,
            "deviation": deviation,
            "magic": 888355,
            "comment": "python script open",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result is None:
            logging.error(f'order_send failed, error code={mt5.last_error()}')
            return False
        elif result.retcode != mt5.TRADE_RETCODE_DONE:
            logging.error(f'order_send failed, retcode={result.retcode}.')
            return False
        logging.info(f'Order placed successfully: {result}')
        return True
    
    def define_strategy(self):
        """    strategy-specifics      """
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name,password=mt_password)
        
        usdx = self.get_hist_data("DX.f", 120).dropna()["close"].rename('usdx')
        symbol_df = self.get_hist_data(self.symbol, 120).dropna()
        symbol_close = symbol_df["close"].rename(self.symbol)
        dfs = [usdx, symbol_close]
        merged_data = reduce(lambda left,right: pd.merge(left,right,left_index=True,right_index=True, how='outer'), dfs)
        merged_data.dropna(inplace=True)

        #price
        self.price = symbol_df["close"].iloc[-1]

        #atr
        atr = talib.ATR(symbol_df['high'].values, symbol_df['low'].values, symbol_df['close'].values, timeperiod=50)
        self.atr = atr[-1]
        
        #z_scores
        spread = merged_data["usdx"] - merged_data[self.symbol]
        rolling_mean = spread.rolling(window=20).mean()
        rolling_std = spread.rolling(window=20).std()
        z_score = (spread - rolling_mean) / rolling_std
        self.z_score = z_score.iloc[-1]

        #logging plus debugging
        print(f"Price:   {self.price}, ATR:  {self.atr}")
        print(f"Z-Score:   {self.z_score}")
    
    def check_position(self, symbol):
        """Checks the most recent position for a specific symbol. Returns True if LONG, False if SHORT."""
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name,password=mt_password)
        positions = mt5.positions_get(symbol=symbol)

        if positions == None or len(positions) == 0:
            print("No positions found for symbol {}".format(symbol))
            return None
        
        # Check the most recent position (last in the list)
        position = positions[-1]

        if position.type == mt5.ORDER_TYPE_BUY:
            print(f'{self.symbol}: Long position')
            return True  # It's a long position
        elif position.type == mt5.ORDER_TYPE_SELL:
            print(f'{self.symbol}: Short position')
            return False  # It's a short position
        
    def execute_trades(self):
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name,password=mt_password)
        self.define_strategy()
        # check if we are invested
        self.Invested = self.check_position(self.symbol)
        #positions_total = mt5.positions_total()
        #if positions_total > 0: 
        #    self.Invested = True

        price = self.price
        z_score = self.z_score
        atr = self.atr
        logging.info(f'Z-score: {z_score}, ATR: {atr}, Last Price:   {price}')
        
        if self.Invested == None:
            if z_score > self.upper_threshold:
                min_stop = round(price + (self.sl_factor * atr), 6)
                target_profit = round(price - (self.tp_factor * atr), 6)
                self.place_order(mt5.ORDER_TYPE_SELL, sl_price= min_stop, tp_price= target_profit)
            elif z_score < self.lower_threshold:
                min_stop = round(price - (self.sl_factor * atr), 6)
                target_profit = round(price + (self.tp_factor * atr), 6)
                self.place_order(mt5.ORDER_TYPE_BUY, sl_price= min_stop, tp_price= target_profit)

if __name__ == "__main__":

    symbol = 'NZDUSD'

    last_action_timestamp = 0
    last_display_timestamp = 0

    trader = MysteryOfTheMissingHeart(symbol, lot_size=0.9)

    while True:
        # Launch the algorithm
        current_timestamp = int(time.time())
        if (current_timestamp - last_action_timestamp) > 3600:#changed to 60 from 3600
            if datetime.now().weekday() not in (5,6):
                if not 23 <= datetime.now().hour <= 3:
                    # Account Info
                    if mt5.initialize(login=mt_login_id, server=mt_server_name, password=mt_password):
                        current_account_info = mt5.account_info()
                        print("------------------------------------------------------------------------------------------")
                        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        if current_account_info is not None:
                            print(f"Balance: {current_account_info.balance} USD,\t"
                                  f"Equity: {current_account_info.equity} USD, \t"
                                  f"Profit: {current_account_info.profit} USD")
                        else:
                            print("Failed to retrieve account information.")
                        print("-------------------------------------------------------------------------------------------")
                    # Look for trades
                    trader.execute_trades()
            last_action_timestamp = int(time.time())
        
        if (current_timestamp - last_display_timestamp) > 3600:
            trader.check_position(symbol)
            last_display_timestamp = int(time.time())
           
        # to avoid excessive cpu usage because loop running lightning fast
        sleep(30)