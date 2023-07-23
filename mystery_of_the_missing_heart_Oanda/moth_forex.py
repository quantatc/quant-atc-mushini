import MetaTrader5 as mt5
import yfinance as yf
from datetime import datetime
import pandas as pd
import numpy as np
from functools import reduce
import talib
import time
from time import sleep
from pytz import timezone
import logging
from dotenv import load_dotenv
import os
import schedule

load_dotenv()
# Load environment variables
mt_login_id = int(os.getenv("mt_login_id2"))
mt_password = os.getenv("mt_password2")
mt_server_name = os.getenv("mt_server_name2")

if not mt_login_id or not mt_password or not mt_server_name:
    raise ValueError("Please set the environment variables METATRADER_LOGIN_ID, METATRADER_PASSWORD and METATRADER_SERVER")

class MysteryOfTheMissingHeart:
    sl_factor = 3
    tp_factor = 1.5
    upper_threshold = 0.5
    lower_threshold = -0.5

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
            return data
        except KeyError:
            print(f"Error: Historical data for symbol '{symbol}' is not available.")
            return pd.DataFrame()  # Return an empty DataFrame
    
    def get_dxy_data(self, symbol= "DX-Y.NYB"):
        data = yf.download(symbol, period="15d", interval="1h")
        data.index.name = 'date'
        usdx_yahoo = data.tail(200)
        usdx_yahoo.columns = map(str.lower, usdx_yahoo.columns)
        usdx_yahoo = usdx_yahoo['close'].dropna().rename('usdx')
        usdx_yahoo = usdx_yahoo[:-1]
        usdx_yahoo.index = usdx_yahoo.index.tz_localize('UTC')
        return usdx_yahoo

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
            "magic": 111311,
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
    
    def define_strategy(self, symbol):
        """    strategy-specifics      """
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name,password=mt_password)
        
        #usdx = self.get_hist_data("DX.f", 120).dropna()["close"].rename('usdx')
        usdx = self.get_dxy_data()
        symbol_df = self.get_hist_data(symbol, 200).dropna()
        if symbol_df.empty:
            print(f"Error: Historical data for symbol '{symbol}' is not available.")
            return None, None, None, None
        symbol_close = symbol_df["close"].rename(symbol)
        symbol_close.index = symbol_close.index.tz_localize('UTC')
        dfs = [usdx, symbol_close]
        merged_data = reduce(lambda left,right: pd.merge(left,right,left_index=True,right_index=True, how='outer'), dfs)
        merged_data.dropna(inplace=True)

        #price
        price = symbol_df["close"].iloc[-1]

        #atr
        atrs = talib.ATR(symbol_df['high'].values, symbol_df['low'].values, symbol_df['close'].values, timeperiod=10)
        atr = atrs[-1]
        
        if not (symbol == self.symbols[0]):
            #z_scores
            spread = merged_data["usdx"] - (1/ merged_data[symbol])
            rolling_mean = spread.rolling(window=20).mean()
            rolling_std = spread.rolling(window=20).std()
            z_scores = (spread - rolling_mean) / rolling_std
            z_score = z_scores.iloc[-1]

            #correlation
            correlation = merged_data['usdx'].rolling(window=20).corr((1/merged_data[symbol]))
            corr = correlation.iloc[-1]
            return price, atr, z_score, corr
        else:
            #z_scores
            spread = merged_data["usdx"] - merged_data[symbol]
            rolling_mean = spread.rolling(window=20).mean()
            rolling_std = spread.rolling(window=20).std()
            z_scores = (spread - rolling_mean) / rolling_std
            z_score = z_scores.iloc[-1]

            #correlation
            correlation = merged_data['usdx'].rolling(window=20).corr(merged_data[symbol])
            corr = correlation.iloc[-1]
            return price, atr, z_score, corr
        #logging plus debugging
        #print(f"Price:   {price}, ATR:  {atr}, Z-Score:   {z_score}")
        
    
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
        
    def execute_trades(self):
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name,password=mt_password)

        for symbol in self.symbols:
            price, atr, z_score, corr = self.define_strategy(symbol)
            if price is None or atr is None or z_score is None or corr is None:
                print(f"Skipping symbol '{symbol}' due to missing strategy data.")
                continue
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                continue
            # check if we are invested
            #self.Invested = self.check_position(symbol)
            logging.info(f'Symbol: {symbol}, Last Price:   {price}, ATR: {atr}, Z-score: {z_score}, Corr: {corr}')
            print(f'Symbol: {symbol}, Last Price:   {price}, ATR: {atr}, Z-score: {z_score}, Corr: {corr}')

            if symbol == self.symbols[1]:
                if corr > 0.1:
                    if z_score > self.upper_threshold:
                        min_stop = round(tick.bid + (self.sl_factor * atr), 5)
                        target_profit = round(tick.bid - (self.tp_factor * atr), 5)
                        self.place_order(symbol=symbol, order_type=mt5.ORDER_TYPE_SELL, sl_price= min_stop, tp_price= target_profit)
                    elif z_score < self.lower_threshold:
                        min_stop = round(tick.ask - (self.sl_factor * atr), 5)
                        target_profit = round(tick.ask + (self.tp_factor * atr), 5)
                        self.place_order(symbol=symbol, order_type=mt5.ORDER_TYPE_BUY, sl_price= min_stop, tp_price= target_profit)
            else:
                if -0.8 < corr < 0.8:
                    if z_score > self.upper_threshold:
                        min_stop = round(tick.bid + (self.sl_factor * atr), 5)
                        target_profit = round(tick.bid - (self.tp_factor * atr), 5)
                        self.place_order(symbol=symbol, order_type=mt5.ORDER_TYPE_SELL, sl_price= min_stop, tp_price= target_profit)
                    elif z_score < self.lower_threshold:
                        min_stop = round(tick.ask - (self.sl_factor * atr), 5)
                        target_profit = round(tick.ask + (self.tp_factor * atr), 5)
                        self.place_order(symbol=symbol, order_type=mt5.ORDER_TYPE_BUY, sl_price= min_stop, tp_price= target_profit)

if __name__ == "__main__":

    symbols = ['USDJPY.sml', 'EURUSD.sml']

    last_action_timestamp = 0
    last_display_timestamp = 0 

    trader = MysteryOfTheMissingHeart(symbols, lot_size=0.02)

    def execute_trades():
        current_datetime = datetime.now()

        if current_datetime.weekday() < 5:  # Monday to Friday
            if 9 <= current_datetime.hour < 15:  # Check for hours 9 to 14 (inclusive)
                if mt5.initialize(login=mt_login_id, server=mt_server_name, password=mt_password):
                    current_account_info = mt5.account_info()
                    print("__________________________________________________________________________________________________")
                    print("MOTH CORR FX: OANDA LIVE ACCOUNT")
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

                print("Open Positions:---------------------------------------------------------------------------------")
                trader.check_position()

    # Schedule the tasks
    schedule.every().hour.at(":03").do(execute_trades)

    while True:
        schedule.run_pending()