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
mt_login_id = int(os.getenv("mt_login_idDERIV"))
mt_password = os.getenv("mt_passwordDERIV")
mt_server_name = os.getenv("mt_server_nameDERIV")
path = os.getenv("pathDERIV")

# if not mt_login_id or not mt_password or not mt_server_name or path:
#     raise ValueError("Please set the environment variables METATRADER_LOGIN_ID, METATRADER_PASSWORD and METATRADER_SERVER")

class MysteryOfTheMissingHeart:
    sl_factor = 1.5
    tp_factor = 2

    def __init__(self, symbols):
        self.symbols = symbols
        self.order_result_comment = None
        self.pos_summary = None
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

    def get_hist_data(self, symbol, n_bars, timeframe=mt5.TIMEFRAME_M15): #changed timeframe
        """ Function to import the data of the chosen symbol"""
        # Initialize the connection if there is not
        mt5.initialize(path=path, login=mt_login_id, server=mt_server_name, password=mt_password)
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
        mt5.initialize(path=path, login=mt_login_id, server=mt_server_name, password=mt_password)
        
        symbol_df = self.get_hist_data(symbol, 500).dropna()
        #convert timezone to UTC
        try:
            symbol_df.index = symbol_df.index.tz_localize('UTC')
        except TypeError:
            print("failed tz_localize, trying tz_convert")
            symbol_df.index = symbol_df.index.tz_convert('UTC')

        if symbol_df.empty:
            print(f"Error: Historical data for symbol '{symbol}' is not available.")
            return None, None
        symbol_df.columns = [col.title() for col in symbol_df.columns]
        #atr
        atr_series = ta.atr(symbol_df['High'], symbol_df['Low'], symbol_df['Close'], length=16)
        atr = atr_series.values[-1]

        # Generate the signals based on the strategy rules
        def generate_signal(ohlc: pd.DataFrame) -> pd.DataFrame:
            # Calculate William Fractals
            ohlc["william_bearish"] =  np.where(ohlc["High"] == ohlc["High"].rolling(3, center=True).max(), ohlc["High"], np.nan)
            ohlc["william_bullish"] =  np.where(ohlc["Low"] == ohlc["Low"].rolling(3, center=True).min(), ohlc["Low"], np.nan)
            
            # Calculate RSI 
            ohlc["rsi"] = ta.rsi(ohlc.Close)

            # Calculate EMAs 
            ohlc["ema50"]   = ta.ema(ohlc.Close, length=50)
            ohlc["ema21"]   = ta.ema(ohlc.Close, length=21)
            ohlc["ema200"]  = ta.ema(ohlc.Close, length=200)
            # Calculate the slopes of the EMAs 
            rolling_period = 10
            ohlc["slope_ema21"] = ohlc["ema21"].diff(periods=1)
            ohlc["slope_ema50"] = ohlc["ema50"].diff(periods=1)
            ohlc["slope_ema200"] = ohlc["ema200"].diff(periods=1)
            ohlc["slope_ema21"] = ohlc["slope_ema21"].rolling(window=rolling_period).mean()
            ohlc["slope_ema50"] = ohlc["slope_ema50"].rolling(window=rolling_period).mean()
            ohlc["slope_ema200"] = ohlc["slope_ema200"].rolling(window=rolling_period).mean()

            # Generate the ema signal
            conditions = [
                ( (ohlc['ema21']<ohlc['ema50']) & (ohlc['ema50']<ohlc['ema200']) & (ohlc['slope_ema21']<0) & (ohlc['slope_ema50']<0) & (ohlc['slope_ema200']<0) ),
                ( (ohlc['ema21']>ohlc['ema50']) & (ohlc['ema50']>ohlc['ema200']) & (ohlc['slope_ema21']>0) & (ohlc['slope_ema50']>0) & (ohlc['slope_ema200']>0) )
                    ]
            choices = [1, 2]
            ohlc['ema_signal'] = np.select(conditions, choices, default=0)

            # Create the buy and sell signal
            signal = [0]*len(ohlc)

            for row in range(0, len(ohlc)):
                signal[row] = 0
                if ohlc.ema_signal[row]==1 and ohlc.rsi[row] < 50 and ohlc.william_bearish[row] > 0 and ohlc.Close[row] < ohlc.ema21[row] and ohlc.Close[row] < ohlc.ema50[row] and ohlc.Close[row] < ohlc.ema200[row]:
                    signal[row]=1

                if ohlc.ema_signal[row]==2 and ohlc.rsi[row] > 50 and ohlc.william_bullish[row] > 0 and ohlc.Close[row] > ohlc.ema21[row] and ohlc.Close[row] > ohlc.ema50[row] and ohlc.Close[row] > ohlc.ema200[row]:
                    signal[row]=2   

            ohlc['signal'] = signal

            return ohlc 

        signals_df = generate_signal(symbol_df)
        # print(signals_df.Close.values[-20:])
        print(signals_df.signal.values[-10:])
        signal_value = signals_df.signal.values[-2]
        # symbol_df['signal'] = signal

        #logging plus debugging
        #print(f"Signals:   {symbol_df['Signal'].tail()}")
        return atr, signal_value
    
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
            "magic": 772473,
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
        mt5.initialize(path = path, login=mt_login_id, server=mt_server_name, password=mt_password)
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
            atr, signal = self.define_strategy(symbol)
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
            
            if symbol == "Step Index":
                lotsize = 0.1
            if symbol == "Volatility 10 Index":
                lotsize = 0.30
            if symbol == "Volatility 25 Index" or symbol == "Volatility 100 Index":
                lotsize = 0.50
            if symbol == "Volatility 75 Index":
                lotsize = 0.001
            if symbol == "Volatility 50 Index":
                lotsize = 4.00
            if signal==2:
                sl = round(tick.ask - (self.sl_factor * atr) - spread, 5)
                tp = round(tick.ask + (self.tp_factor * atr) + spread, 5)
                self.place_order(symbol=symbol, order_type=mt5.ORDER_TYPE_BUY, sl_price=sl, tp_price=tp, lotsize=lotsize)
            if signal==1:
                sl = round(tick.bid + (self.sl_factor * atr) + spread, 5)
                tp = round(tick.bid - (self.tp_factor * atr) - spread, 5)
                self.place_order(symbol=symbol, order_type=mt5.ORDER_TYPE_SELL, sl_price=sl, tp_price=tp, lotsize=lotsize)
        
        # signals_df.to_csv("volatilitysignals_df.csv")

if __name__ == "__main__":
    symbols = ["Volatility 10 Index", "Step Index",  "Volatility 25 Index", "Volatility 50 Index", "Volatility 75 Index", "Volatility 100 Index"] 
    last_action_timestamp = 0
    last_display_timestamp = 0
    trader = MysteryOfTheMissingHeart(symbols)
    while True:
        current_time = datetime.now()
        # Launch the algorithm
        current_timestamp = int(time.time())
        if (current_timestamp - last_action_timestamp) >= 900:
            start_time = time.time()
            # Account Info
            if mt5.initialize(path=path, login=mt_login_id, server=mt_server_name, password=mt_password):
                current_account_info = mt5.account_info()
                print("_______________________________________________________________________________________________________")
                print("DERIV DEMO ACCOUNT: MOMENTUM SCALPING STRATEGY")
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