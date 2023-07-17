import MetaTrader5 as mt5
import yfinance as yf
from datetime import datetime
import pandas as pd
import numpy as np
from functools import reduce
from vasof_indicator import Vasof
import talib
import time
from time import sleep
from pytz import timezone
import logging
from dotenv import load_dotenv
import os

load_dotenv()
# Load environment variables
mt_login_id = int(os.getenv("mt_login_id3"))
mt_password = os.getenv("mt_password3")
mt_server_name = os.getenv("mt_server_name3")

if not mt_login_id or not mt_password or not mt_server_name:
    raise ValueError("Please set the environment variables METATRADER_LOGIN_ID, METATRADER_PASSWORD and METATRADER_SERVER")

class MysteryOfTheMissingHeart:
    sl_factor = 2
    tp_factor = 1
    quantile = 0.3
    lower_fib_thres = 10
    high_fib_thres = 95
    thresold = 0.0032

    def __init__(self, symbols, lot_size):
        self.symbols = symbols
        self.lot = lot_size
        self.order_result_comment = None
        self.pos_summary = None
        #self.Invested = None
        if not mt5.initialize(login=mt_login_id, server=mt_server_name, password=mt_password):
            print("initialize() failed, error code =",mt5.last_error())
            quit()
        for symbol in self.symbols:
            if self.check_symbol(symbol):
                print(f"Symbol {symbol} is in the Market Watch.")
            
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
        try:
            #get data and convert it into pandas dataframe
            utc_from = datetime.now()
            rates = mt5.copy_rates_from(symbol, timeframe, utc_from, n_bars)
            data = pd.DataFrame(rates)
            data['time'] = pd.to_datetime(data['time'], unit='s')
            data['time'] = pd.to_datetime(data['time'], format='%Y-%m-%d')
            data = data.set_index('time')
            data = data[['open', 'high', 'low', 'close']]
            return data
        except KeyError:
            print(f"Error: Historical data for symbol '{symbol}' is not available.")
            return pd.DataFrame()  # Return an empty DataFrame

    def place_order(self, symbol, order_type, sl_price, tp_price):
        #point = mt5.symbol_info(self.symbol).point
        #price = mt5.symbol_info_tick(self.symbol).last
        deviation = 20
        tick = mt5.symbol_info_tick(symbol)
        symbol_info = mt5.symbol_info(symbol)
        
        if order_type == mt5.ORDER_TYPE_BUY:
            price = tick.ask
        elif order_type == mt5.ORDER_TYPE_SELL:
            price = tick.bid
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": self.lot,
            "type": order_type,
            "price": price,
            "sl": sl_price,
            "tp": tp_price,
            "deviation": deviation,
            "magic": 271667,
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
    
    def close_positions(self, position):
        """ Function to close a specific position """
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name, password=mt_password)

        tick = mt5.symbol_info_tick(position.symbol)
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": mt5.ORDER_TYPE_BUY if position.type == mt5.ORDER_TYPE_SELL else mt5.ORDER_TYPE_SELL,
            "position": position.ticket,
            "price": tick.ask if position.type == mt5.ORDER_TYPE_BUY else tick.bid,
            "deviation": 20,
            "magic": 444556,
            "comment": "correlation algo order",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        # Send a trading request
        result = mt5.order_send(request)
        if result is None:
            print("Failed to close position.")
        elif result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Failed to close position: {result.comment}")
        else:
            print(f"Closed position: {position.symbol} ({position.volume} lots)")
    
    def define_strategy(self, symbol):
        """    strategy-specifics      """
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name,password=mt_password)
        
        df = self.get_hist_data(symbol, 2000).dropna()
        if df.empty:
            print(f"Error: Historical data for symbol '{symbol}' is not available.")
            return None, None, None, None, None
        
        vasof_instance = Vasof(df)
        vasof_instance.adder(3)
        vasof_instance.fib_stoch(20, 4, 5)
        my_data = vasof_instance.data
        df = pd.DataFrame(my_data, columns = ["Date", "Open", "High", "Low", "Close", "std", "nstd", "fib_stoch"])
        df.set_index("Date", inplace = True)
        df.index = pd.to_datetime(df.index)
        df = df.apply(pd.to_numeric)
        df.dropna(inplace = True)
        #fractal analysis params...........................................................
        ema_lookback = 20
        min_max_lookback = 14
        #..................................................................................
        df['ema_high'] = df.High.ewm(span=ema_lookback, adjust=False).mean() 
        df['ema_low'] = df.Low.ewm(span=ema_lookback, adjust=False).mean() 
        df['volatility_high'] =  df.High.rolling(ema_lookback).std()
        df['volatility_low'] = df.Low.rolling(ema_lookback).std()
        df['MAX'] = (df.High - df.ema_high).rolling(min_max_lookback).max()
        df['MIN'] = (df.Low - df.ema_low).rolling(min_max_lookback).min()
        df.dropna(inplace = True)
        df['fractal'] = (df.MAX - df.MIN) / ((df.volatility_high + df.volatility_low)/2)
        df = df.drop(columns = ["std", "nstd", 'ema_high', 'ema_low', 'volatility_high', 'volatility_low', 'MAX', 'MIN'])

        #price
        price = df["Close"].iloc[-1]
        #fractal value
        fractal = df['fractal'].iloc[-1]
        #vasof value
        vasof = df['fib_stoch'].iloc[-1]
        #atr
        true_range = talib.ATR(df['High'].values, df['Low'].values, df['Close'].values, timeperiod=50)
        atr = true_range[-1]
        #bolinger bands for trend
        upperband, middleband, lowerband = talib.BBANDS(df.Close.values, timeperiod=20, matype=1)
        df['trend'] = upperband - lowerband
        trend = df.trend.values[-1]

        #logging plus debugging
        #print(f"Price:   {price}, ATR:  {atr}, Fractal: {fractal}, Vasof: {vasof}, Trend: {trend}")
        return price, atr, fractal, vasof, trend
    
    def check_position(self):
        """Checks the most recent position for each symbol and prints the count of long and short positions."""
        # Initialize the connection if it is not already initialized
        mt5.initialize(login=mt_login_id, server=mt_server_name, password=mt_password)

        for symbol in self.symbols:
            positions = mt5.positions_get(symbol=symbol)
            if positions is None or len(positions) == 0:
                print(f"No positions found for symbol {symbol}")
            else:
                long_positions = sum(position.type == mt5.ORDER_TYPE_BUY for position in positions)
                short_positions = sum(position.type == mt5.ORDER_TYPE_SELL for position in positions)
                print(f"Positions for symbol {symbol}:")
                print(f"  Long positions: {long_positions}")
                print(f"  Short positions: {short_positions}")
        
        print("--------------------------------------------------------------------------------------------------")
    
    def close_all_positions(self):
        """ Function to close all open positions """
        mt5.initialize(login=mt_login_id, server=mt_server_name, password=mt_password)
        positions = mt5.positions_get()
        if positions is None or len(positions) == 0:
            print("No open positions to close.")
        else:
            for position in positions:
                self.close_positions(position)
        
    def execute_trades(self):
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name,password=mt_password)
        for symbol in self.symbols:
            price, atr, fractal, vasof, trend = self.define_strategy(symbol)
            if price is None or atr is None or vasof is None or fractal is None:
                print(f"Skipping symbol '{symbol}' due to missing strategy data.")
                continue
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                continue
            #logging strategy values
            logging.info(f"Price:   {price}, ATR:  {atr}, Fractal: {fractal}, Vasof: {vasof}, Trend: {trend}")
            print(f"Price:   {price}, ATR:  {atr}, Fractal: {fractal}, Vasof: {vasof}, Trend: {trend}")
            
            if  trend > self.thresold and fractal >= 1.5 and fractal <= 3.5:
                if vasof <= self.lower_fib_thres:
                    min_stop = round(tick.ask - (self.sl_factor * atr), 5)
                    target_profit = round(tick.ask + (self.tp_factor * atr), 5)
                    self.place_order(symbol=symbol, order_type=mt5.ORDER_TYPE_BUY, sl_price= min_stop, tp_price= target_profit)
                if vasof >= self.high_fib_thres:
                    min_stop = round(tick.bid + (self.sl_factor * atr), 5)
                    target_profit = round(tick.bid - (self.tp_factor * atr), 5)
                    self.place_order(symbol=symbol, order_type=mt5.ORDER_TYPE_SELL, sl_price= min_stop, tp_price= target_profit)
                    
                
if __name__ == "__main__":

    symbols = ['CADCHFm', 'CHFJPYm', 'EURCHFm', 'GBPNZDm', 'NZDCADm', 'NZDCHFm']

    last_action_timestamp = 0
    last_display_timestamp = 0

    trader = MysteryOfTheMissingHeart(symbols, lot_size=0.01)

    while True:
        # Launch the algorithm
        current_timestamp = int(time.time())
        current_datetime = datetime.now()

        if (current_timestamp - last_action_timestamp) > 3600: # changed to 60 from 3600
            if current_datetime.weekday() == 4 and current_datetime.hour >= 22:  # Friday after 10 PM
                trader.close_all_positions()
            elif 0 <= current_datetime.weekday() <= 4:  # Monday to Friday
                if not (23 <= current_datetime.hour <= 3):  # Not between 11 PM and 3 AM
                    # Account Info
                    if mt5.initialize(login=mt_login_id, server=mt_server_name, password=mt_password):
                        current_account_info = mt5.account_info()
                        print("__________________________________________________________________________________________________")
                        print("MOTH VASOF STRATEGY: DEMO ACCOUNT: ")
                        print("__________________________________________________________________________________________________")
                        print(f"Date: {current_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
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
            print("Open Positions:---------------------------------------------------------------------------------")
            trader.check_position()
            last_display_timestamp = int(time.time())

        # to avoid excessive CPU usage because the loop is running too fast
        time.sleep(15)