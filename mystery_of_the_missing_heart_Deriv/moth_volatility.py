import MetaTrader5 as mt5
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

load_dotenv()
# Load environment variables
mt_login_id = int(os.getenv("mt_login_id7"))
mt_password = os.getenv("mt_password7")
mt_server_name = os.getenv("mt_server_name7")

if not mt_login_id or not mt_password or not mt_server_name:
    raise ValueError("Please set the environment variables METATRADER_LOGIN_ID, METATRADER_PASSWORD and METATRADER_SERVER")

class MysteryOfTheMissingHeart:
    sl_factor = 1.5
    tp_factor = 2.5
    BCount = 1
    PullBack = 1
    ExitBars = 1

    def __init__(self, symbols):
        self.symbols = symbols
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

    def get_hist_data(self, symbol, n_bars, timeframe=mt5.TIMEFRAME_M15): #changed timeframe
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

    def place_order(self, symbol, order_type, sl_price, tp_price, lotsize):
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
            "volume": lotsize,
            "type": order_type,
            "price": price,
            "sl": sl_price,
            "tp": tp_price,
            "deviation": deviation,
            "magic": 772473,
            "comment": "python script open",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
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
        
        symbol_df = self.get_hist_data(symbol, 1200).dropna()
        # Generate the signals based on the strategy rules
        symbol_df['up_closes'] = symbol_df['close'] - symbol_df['open'] > 0
        symbol_df['down_closes'] = symbol_df['close'] - symbol_df['open'] < 0
        symbol_df['Signal'] = 0
        symbol_df.loc[symbol_df['up_closes'].rolling(window=self.BCount).sum() > symbol_df['down_closes'].rolling(window=self.BCount).sum(), 'Signal'] = 1
        symbol_df.loc[symbol_df['up_closes'].rolling(window=self.BCount).sum() < symbol_df['down_closes'].rolling(window=self.BCount).sum(), 'Signal'] = -1
        symbol_df['Signal'] = symbol_df['Signal'].shift(-self.PullBack)
        
        # Drop unnecessary columns
        symbol_df.drop(['up_closes', 'down_closes'], axis=1, inplace=True)
        # Remove NaN values
        symbol_df.dropna(inplace=True)

        #atr
        atrs = talib.ATR(symbol_df['high'].values, symbol_df['low'].values, symbol_df['close'].values, timeperiod=50)
        atr = atrs[-1]
        
        #z_scores
        signal = symbol_df['Signal'].iloc[-1]

        #logging plus debugging
        #print(f"Signals:   {symbol_df['Signal'].tail()}")
        return atr, signal
    
    def check_position(self):
        """Checks the most recent position for a specific symbol. Returns True if LONG, False if SHORT."""
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name,password=mt_password)

        for symbol in self.symbols:
            positions = mt5.positions_get(symbol=symbol)

            if positions == None or len(positions) == 0:
                print("No positions found for symbol {}".format(symbol))
                return None
            
            # Check the most recent position (last in the list)
            #position = positions[-1]
            for position in positions:
                if position.type == mt5.ORDER_TYPE_BUY:
                    print(f'{symbol}: Long position')
                    return True  # It's a long position
                elif position.type == mt5.ORDER_TYPE_SELL:
                    print(f'{symbol}: Short position')
                    return False  # It's a short position
        
    def execute_trades(self):
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name,password=mt_password)

        for symbol in self.symbols:
            atr, signal = self.define_strategy(symbol)
            tick = mt5.symbol_info_tick(symbol)
            # check if we are invested
            #self.Invested = self.check_position(symbol)
            logging.info(f'Symbol: {symbol}, Last Price:   {tick.ask}, ATR: {atr}, Signal: {signal}')
            print(f'Symbol: {symbol}, Last Price:   {tick.ask}, ATR: {atr}, Signal: {signal}')
            lotsize = None
            
            if symbol == "Step Index":
                lotsize == 0.1
            if symbol == "Volatility 10 Index":
                lotsize == 0.50
            if symbol == "Volatility 25 Index":
                lotsize == 0.70
            
            if signal==1:
                min_stop = round(tick.bid - (self.sl_factor * atr), 5)
                target_profit = round(tick.bid + (self.tp_factor * atr), 5)
                self.place_order(symbol=symbol, order_type=mt5.ORDER_TYPE_BUY, sl_price= min_stop, tp_price= target_profit, lotsize=lotsize)
          
            if signal==-1:
                min_stop = round(tick.ask + (self.sl_factor * atr), 5)
                target_profit = round(tick.ask - (self.tp_factor * atr), 5)
                self.place_order(symbol=symbol, order_type=mt5.ORDER_TYPE_SELL, sl_price= min_stop, tp_price= target_profit, lotsize=lotsize)
            

if __name__ == "__main__":

    symbols = ["Step Index", "Volatility 10 Index", "Volatility 25 Index"]

    last_action_timestamp = 0
    last_display_timestamp = 0

    trader = MysteryOfTheMissingHeart(symbols)

    while True:
        # Launch the algorithm
        current_timestamp = int(time.time())
        if (current_timestamp - last_action_timestamp) > 900:
            # Account Info
            if mt5.initialize(login=mt_login_id, server=mt_server_name, password=mt_password):
                current_account_info = mt5.account_info()
                print("------------------------------------------------------------------------------------------")
                print("DERIV: MOMENTUM SCALPING STRATEGY")
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
        
        if (current_timestamp - last_display_timestamp) > 900:
            trader.check_position()
            last_display_timestamp = int(time.time())
           
        # to avoid excessive cpu usage because loop running lightning fast
        sleep(1)