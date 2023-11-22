import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import time
import logging
from dotenv import load_dotenv
import os
import pandas_ta as ta

load_dotenv()
# Load environment variables
mt_login_id = int(os.getenv("mt_login_idXM"))
mt_password = os.getenv("mt_passwordXM")
mt_server_name = os.getenv("mt_server_nameXM")
path = os.getenv("pathXM")

# if not mt_login_id or not mt_password or not mt_server_name or path:
#     raise ValueError("Please set the environment variables METATRADER_LOGIN_ID, METATRADER_PASSWORD and METATRADER_SERVER")

class MysteryOfTheMissingHeart:
    sl_factor = 2
    tp_factor = 2

    def __init__(self, symbols):
        self.symbols = symbols
        #self.Invested = None
        if not mt5.initialize(path=path, login=mt_login_id, server=mt_server_name, password=mt_password):
            print("initialize() failed, error code =",mt5.last_error())
            quit()
        for symbol in self.symbols:
            if self.check_symbol(symbol):
                print(f"Symbol {symbol} is in the Market Watch.")
            
    def check_symbol(self, symbol):
        """Checks if a symbol is in the Market Watch. If it's not, the symbol is added."""
        # Initialize the connection if there is not
        mt5.initialize(path=path, login=mt_login_id, server=mt_server_name, password=mt_password)
        symbols = mt5.symbols_get()
        symbol_list = [s.name for s in symbols]
        if symbol not in symbol_list:
            print("Symbol {} not found in Market Watch. Adding it...".format(symbol))
            if not mt5.symbol_select(symbol, True):
                print("Failed to add {} to Market Watch".format(symbol))
                return False
        return True

    def get_hist_data(self, symbol, n_bars, timeframe=mt5.TIMEFRAME_M1): #changed timeframe
        """ Function to import the data of the chosen symbol"""
        # Initialize the connection if there is not
        mt5.initialize(path=path, login=mt_login_id, server=mt_server_name, password=mt_password)
        try:
            #get data and convert it into pandas dataframe
            utc_from = datetime.utcnow()
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
        mt5.initialize(path=path, login=mt_login_id, server=mt_server_name, password=mt_password)
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
        mt5.initialize(path=path, login=mt_login_id, server=mt_server_name, password=mt_password)
        
        symbol_df = self.get_hist_data(symbol, 500).dropna()
        if symbol_df.empty:
            print(f"Error: Historical data for symbol '{symbol}' is not available.")
            return None, None
        symbol_df.columns = [col.title() for col in symbol_df.columns]
        # Generate the signals based on the strategy rules
        # symbol_df = self.generate_signal(symbol_df)
        # Calculate William Fractals
        symbol_df["william_bearish"] =  np.where(symbol_df["High"] == symbol_df["High"].rolling(9, center=True).max(), symbol_df["High"], np.nan)
        symbol_df["william_bullish"] =  np.where(symbol_df["Low"] == symbol_df["Low"].rolling(9, center=True).min(), symbol_df["Low"], np.nan)
        # Calculate RSI 
        symbol_df["rsi"] = ta.rsi(symbol_df.Close)
        # Calculate EMAs 
        symbol_df["ema50"]   = ta.ema(symbol_df.Close, length=50)
        symbol_df["ema21"]   = ta.ema(symbol_df.Close, length=21)
        symbol_df["ema200"]  = ta.ema(symbol_df.Close, length=200)
        # Calculate the slopes of the EMAs 
        rolling_period = 10
        symbol_df["slope_ema21"] = symbol_df["ema21"].diff(periods=1)
        symbol_df["slope_ema50"] = symbol_df["ema50"].diff(periods=1)
        symbol_df["slope_ema200"] = symbol_df["ema200"].diff(periods=1)

        symbol_df["slope_ema21"] = symbol_df["slope_ema21"].rolling(window=rolling_period).mean()
        symbol_df["slope_ema50"] = symbol_df["slope_ema50"].rolling(window=rolling_period).mean()
        symbol_df["slope_ema200"] = symbol_df["slope_ema200"].rolling(window=rolling_period).mean()
        # Generate the ema signal
        conditions = [
            ( (symbol_df['ema21']<symbol_df['ema50']) & (symbol_df['ema50']<symbol_df['ema200']) & (symbol_df['slope_ema21']<0) & (symbol_df['slope_ema50']<0) & (symbol_df['slope_ema200']<0) ),
            ( (symbol_df['ema21']>symbol_df['ema50']) & (symbol_df['ema50']>symbol_df['ema200']) & (symbol_df['slope_ema21']>0) & (symbol_df['slope_ema50']>0) & (symbol_df['slope_ema200']>0) )
                ]
        choices = [-1, 1]
        symbol_df['ema_signal'] = np.select(conditions, choices, default=0)
        # Create the buy and sell signal
        signal = [0]*len(symbol_df)

        for row in range(0, len(symbol_df)):
            signal[row] = 0
            if symbol_df.ema_signal[row]==-1 and symbol_df.rsi[row] < 50 and symbol_df.william_bearish[row] > 0 and symbol_df.Close[row] < symbol_df.ema21[row] and symbol_df.Close[row] < symbol_df.ema50[row] and symbol_df.Close[row] < symbol_df.ema200[row]:
                signal[row]=-1

            if symbol_df.ema_signal[row]==1 and symbol_df.rsi[row] > 50 and symbol_df.william_bullish[row] > 0 and symbol_df.Close[row] > symbol_df.ema21[row] and symbol_df.Close[row] > symbol_df.ema50[row] and symbol_df.Close[row] > symbol_df.ema200[row]:
                signal[row]=1   

        symbol_df['signal'] = signal

        #atr
        atr_series = ta.atr(symbol_df['High'], symbol_df['Low'], symbol_df['Close'], length=16)
        atr = atr_series.values[-1]

        #logging plus debugging
        #print(f"Signals:   {symbol_df['Signal'].tail()}")
        return atr, symbol_df['signal']
    
    def close_positions(self, position):
        """ Function to close a specific position """
        # Initialize the connection if there is not
        mt5.initialize(path=path, login=mt_login_id, server=mt_server_name, password=mt_password)

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
    
    def close_all_positions(self):
        """ Function to close all open positions """
        mt5.initialize(path=path, login=mt_login_id, server=mt_server_name, password=mt_password)
        positions = mt5.positions_get()
        if positions is None or len(positions) == 0:
            print("No open positions to close.")
        else:
            for position in positions:
                self.close_positions(position)
    
    def check_position(self):
        """Checks the most recent position for each symbol and prints the count of long and short positions."""
        # Initialize the connection if it is not already initialized
        mt5.initialize(path=path, login=mt_login_id, server=mt_server_name, password=mt_password)

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
        mt5.initialize(path=path, login=mt_login_id, server=mt_server_name, password=mt_password)

        # signals_df = pd.DataFrame()
        for symbol in self.symbols:
            atr, signals = self.define_strategy(symbol)
            signal = signals.iloc[-2]
            # signals_df[f"{symbol}"] = signals
            if atr is None or signal is None:
                print(f"Skipping symbol '{symbol}' due to missing strategy data.")
                continue
            tick = mt5.symbol_info_tick(symbol)
            if tick is None: continue
            # check if we are invested
            #self.Invested = self.check_position(symbol)
            logging.info(f'Symbol: {symbol}, Last Price:   {tick.ask}, ATR: {atr}, Signal: {signal}')
            print(f'Symbol: {symbol}, Last Price: {tick.ask}, ATR: {atr}, Signal: {signal}')

            spread = abs(tick.bid-tick.ask)
            
            if symbol in self.symbols[:3]:
                lotsize = 0.1
            if symbol in self.symbols[3:]:
                lotsize = 0.02

            if signal==1:
                sl = round(tick.ask - (self.sl_factor * atr) - spread, 5)
                tp = round(tick.ask + (self.tp_factor * atr) + spread, 5)
                self.place_order(symbol=symbol, order_type=mt5.ORDER_TYPE_BUY, sl_price=sl, tp_price=tp, lotsize=lotsize)
            if signal==-1:
                sl = round(tick.bid + (self.sl_factor * atr) + spread, 5)
                tp = round(tick.bid - (self.tp_factor * atr) - spread, 5)
                self.place_order(symbol=symbol, order_type=mt5.ORDER_TYPE_SELL, sl_price=sl, tp_price=tp, lotsize=lotsize)
        
        # signals_df.to_csv("fxcfdsignals_df.csv")

if __name__ == "__main__":
    symbols = ["US100Cash", "GER40Cash", "US30Cash", "GBPUSD", "USDJPY", "EURUSD"] 
    last_action_timestamp = 0
    last_display_timestamp = 0
    trader = MysteryOfTheMissingHeart(symbols)
    while True:
        current_time = datetime.now()
        # Launch the algorithm
        current_timestamp = int(time.time())
        if (current_timestamp - last_action_timestamp) >= 60:
            start_time = time.time()
            # Account Info
            if mt5.initialize(path=path, login=mt_login_id, server=mt_server_name, password=mt_password):
                current_account_info = mt5.account_info()
                print("_______________________________________________________________________________________________________")
                print("XM DEMO ACCOUNT: MOTH SCALPING101 STRATEGY")
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