import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import time
import logging
import pandas_ta as ta
from functools import reduce

class MysteryOfTheMissingHeart:
    sl_factor = 2.8
    tp_factor = 1.6
    upper_threshold = -1.5
    lower_threshold = 1.5

    def __init__(self, symbols):
        self.symbols = symbols
        self.order_result_comment = None
        self.pos_summary = None
        #self.Invested = None
        if not mt5.initialize():
            print("initialize() failed, error code =",mt5.last_error())
            quit()
        for symbol in self.symbols:
            if self.check_symbol(symbol):
                print(f"Symbol {symbol} is in the Market Watch.")
            
    def check_symbol(self, symbol):
        """Checks if a symbol is in the Market Watch. If it's not, the symbol is added."""
        # Initialize the connection if there is not
        mt5.initialize()
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
        mt5.initialize()
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

    def place_order(self, symbol, order_type, sl_price, tp_price, lotsize):
        mt5.initialize()
        #point = mt5.symbol_info(self.symbol).point
        #price = mt5.symbol_info_tick(self.symbol).last
        deviation = 20
        tick = mt5.symbol_info_tick(symbol)
        symbol_info = mt5.symbol_info(symbol)

        if tick is None:
            logging.error(f'order_send failed, error code={mt5.last_error()}')
            return False
        
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
            "magic": 199308,
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
    
    def generate_z_scores(self, symbol):
        rename_list = ['eurusd', 'usdchf', 'audusd', 'usdcad']
        #df = self.get_hist_data(symbol, 500)
        #print(df.head())
        
        dfs = [self.get_hist_data(self.symbols[i], 500)['close'].rename(rename_list[i]) for i in range(len(rename_list))]
        merged_data = reduce(lambda left,right: pd.merge(left,right,left_index=True,right_index=True, how='outer'), dfs)
        merged_data.dropna(inplace=True)
        merged_data['chfusd'] = 1/ merged_data['usdchf']
        merged_data['cadusd'] = 1/ merged_data['usdcad']
        #print(list(merged_data.columns))

        if symbol in self.symbols[:2]:
            # Calculate the spread between euro-swiss pairs
            spread = merged_data['chfusd'] - merged_data['eurusd']
            rolling_mean = spread.rolling(window=20).mean()
            rolling_std = spread.rolling(window=20).std()
            # Calculate the z-score
            z_score = (spread - rolling_mean) / rolling_std

        if symbol in self.symbols[2:]:
            # Calculate the spread between comnodity pairs
            spread = merged_data['cadusd'] - merged_data['audusd']
            rolling_mean = spread.rolling(window=20).mean()
            rolling_std = spread.rolling(window=20).std()
            # Calculate the z-score
            z_score = (spread - rolling_mean) / rolling_std
        
        return z_score
        

    def define_strategy(self, symbol):
        """    strategy-specifics      """
        # Initialize the connection if there is not
        mt5.initialize()
        
        symbol_df = self.get_hist_data(symbol, 500).dropna()
        
        if symbol_df.empty:
            print(f"Error: Historical data for symbol '{symbol}' is not available.")
            return None, None, None, None
        symbol_df.columns = [col.title() for col in symbol_df.columns]
        # Generate the signals based on the strategy rules
        z_scores = self.generate_z_scores(symbol)
        z_score = z_scores[-1]

        # Calculate EMAs 
        ema9   = ta.ema(symbol_df.Close, length=9)
        ema50   = ta.ema(symbol_df.Close, length=50)
        ema200  = ta.ema(symbol_df.Close, length=200)
        ma9 = ema9[-1]
        ma50 = ema50 [-1]
        ma200 = ema200 [-1]
        price = symbol_df.Close[-1]
        ma_uptrend = price > ma9 and ma9 > ma50 and ma50 > ma200
        ma_downtrend = price < ma9 and ma9 < ma50 and ma50 < ma200

        #atr
        atr_series = ta.atr(symbol_df['High'], symbol_df['Low'], symbol_df['Close'], length=16)
        atr = atr_series.values[-1]

        #logging plus debugging
        #print(f"Signals:   {symbol_df['Signal'].tail()}")
        return atr, z_score, ma_uptrend, ma_downtrend
    
    def close_positions(self, position):
        """ Function to close a specific position """
        # Initialize the connection if there is not
        mt5.initialize()

        tick = mt5.symbol_info_tick(position.symbol)
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": mt5.ORDER_TYPE_BUY if position.type == mt5.ORDER_TYPE_SELL else mt5.ORDER_TYPE_SELL,
            "position": position.ticket,
            "price": tick.ask if position.type == mt5.ORDER_TYPE_BUY else tick.bid,
            "deviation": 20,
            "magic": 199308,
            "comment": "correlation algo order",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        # Send a trading request
        result = mt5.order_send(request)
        if result is None:
            print("Failed to close position.")
        elif result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Failed to close position: {result.comment}")
        else:
            print(f"Closed position: {position.symbol} ({position.volume} lots)")
    
    def close_all_positions(self):
        """ Function to close all open positions """
        mt5.initialize()
        positions = mt5.positions_get()
        if positions is None or len(positions) == 0:
            print("No open positions to close.")
        else:
            for position in positions:
                self.close_positions(position)
    
    def check_position(self):
        """Checks the most recent position for each symbol and prints the count of long and short positions."""
        # Initialize the connection if it is not already initialized
        mt5.initialize()

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
        mt5.initialize()

        # signals_df = pd.DataFrame()
        for symbol in self.symbols:
            if symbol not in [self.symbols[0], self.symbols[2]]: continue
            atr, z_score, ma_uptrend, ma_downtrend = self.define_strategy(symbol)
            if atr is None or z_score is None:
                print(f"Skipping symbol '{symbol}' due to missing strategy data.")
                continue
            tick = mt5.symbol_info_tick(symbol)
            if tick is None: continue
            # check if we are invested
            #self.Invested = self.check_position(symbol)
            #logging.info(f'Symbol: {symbol}, Last Price:   {tick.ask}, ATR: {atr}, Signal: {signal}')
            print(f'Symbol: {symbol}, Last Price: {tick.ask}, ATR: {atr}, Z_score: {z_score}')

            spread = abs(tick.bid-tick.ask)
            lotsize = 0.10

            if z_score < self.lower_threshold and ma_uptrend:
                sl = round(tick.ask - (self.sl_factor * atr) - spread, 5)
                tp = round(tick.ask + (self.tp_factor * atr) + spread, 5)
                self.place_order(symbol=symbol, order_type=mt5.ORDER_TYPE_BUY, sl_price=sl, tp_price=tp, lotsize=lotsize)
            if z_score > self.upper_threshold and ma_downtrend:
                sl = round(tick.bid + (self.sl_factor * atr) + spread, 5)
                tp = round(tick.bid - (self.tp_factor * atr) - spread, 5)
                self.place_order(symbol=symbol, order_type=mt5.ORDER_TYPE_SELL, sl_price=sl, tp_price=tp, lotsize=lotsize)

if __name__ == "__main__":
    symbols = ["EURUSD", "USDCHF", "AUDUSD", "USDCAD"] 
    last_action_timestamp = 0
    last_display_timestamp = 0
    trader = MysteryOfTheMissingHeart(symbols)
    while True:
        current_time = datetime.now()
        # Launch the algorithm
        current_timestamp = int(time.time())
        if (current_timestamp - last_action_timestamp) >= 3600:
            start_time = time.time()
            # Account Info
            if mt5.initialize():
                current_account_info = mt5.account_info()
                print("_______________________________________________________________________________________________________")
                print("FundedNext DEMO ACCOUNT: MOTH ADVANCED PAIRS STRATEGY")
                print("_______________________________________________________________________________________________________")
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
                print("Open Positions:---------------------------------------------------------------------------------")
    
                trader.check_position()
                execution_time = time.time() - start_time
                last_action_timestamp = int(time.time()) - (execution_time)
