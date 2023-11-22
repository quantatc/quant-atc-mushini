from binance.client import Client
# from binance import ThreadedWebsocketManager
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
from dotenv import load_dotenv
import logging
import pandas_ta as ta

load_dotenv()
# Load environment variables
api_key = os.getenv("api_key")
secret_key = os.getenv("secret_key")

# if not api_key or not secret_key:
#     raise ValueError("Please set the environment variables api_key, secret_key")

class MysteryOfTheMissingHeart:
    sl_factor = 1
    tp_factor = 1

    def __init__(self, symbols, units, leverage = 5):
        #Initialize client request
        client = Client(api_key = api_key, api_secret = secret_key, tld = "com", testnet = True) #  testnet = True

        self.symbols = symbols
        self.available_intervals = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
        self.units = units
        self.leverage = leverage 
        self.cum_profits = 0

        #set the account to hedging
        # position_mode = client.futures_get_position_mode()
        # if not position_mode['dualSidePosition']:
        #     client.futures_change_position_mode(dualSidePosition = True)

        #*****************add strategy-specific attributes here******************
        self.atr_period = 16

        #************************************************************************


    def get_hist_data(self, symbol, days, interval="5m"): #changed timeframe
        """ Function to import the data of the chosen symbol"""
        # Initialize the connection if there is not
        client = Client(api_key = api_key, api_secret = secret_key, tld = "com", testnet = True) #  testnet = True
        now = datetime.utcnow()
        past = str(now - timedelta(days = days))
    
        bars = client.futures_historical_klines(symbol = symbol, interval = interval,
                                            start_str = past, end_str = None, limit = 1000) # Adj: futures_historical_klines
        df = pd.DataFrame(bars)
        df["Date"] = pd.to_datetime(df.iloc[:,0], unit = "ms")
        df.columns = ["Open Time", "Open", "High", "Low", "Close", "Volume",
                      "Clos Time", "Quote Asset Volume", "Number of Trades",
                      "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore", "Date"]
        df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
        df.set_index("Date", inplace = True)
        for column in df.columns:
            df[column] = pd.to_numeric(df[column], errors = "coerce")
        df["Complete"] = [True for row in range(len(df)-1)] + [False]
        if not df["Complete"].iloc[-1]:
            df = df[:-1]
        
        return df
    
    def define_strategy(self, symbol):
        """    strategy-specifics      """
        # Initialize the connection if there is not
        
        symbol_df = self.get_hist_data(symbol, 2).dropna()
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
            ohlc["william_bearish"] =  np.where(ohlc["High"] == ohlc["High"].rolling(9, center=True).max(), ohlc["High"], np.nan)
            ohlc["william_bullish"] =  np.where(ohlc["Low"] == ohlc["Low"].rolling(9, center=True).min(), ohlc["Low"], np.nan)
            
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
        # print(signals_df.signal.values[-20:])
        signal_value = signals_df.signal.values[-5]
        # symbol_df['signal'] = signal

        #logging plus debugging
        #print(f"Signals:   {symbol_df['Signal'].tail()}")
        return atr, signal_value

    def place_order(self, symbol, side, position, units, stop_loss, take_profit):
        """
        Places a market order on Binance Futures with a stop loss and take profit.
        """
        # Initialize the client
        client = Client(api_key=api_key, api_secret=secret_key, tld="com", testnet=True)
        try:
            # Place the market order
            order = client.futures_create_order(
                symbol=symbol,
                side=side,
                type=Client.ORDER_TYPE_MARKET,
                quantity=units,
                positionSide=position
            )
            # Determine the order side for SL and TP
            opposite_side = "SELL" if order["side"] == "BUY" else "BUY"
            opposite_pos = "LONG" if order['positionSide'] == "LONG" else "SHORT"
            # Create a stop loss order
            client.futures_create_order(
                symbol=symbol,
                side=opposite_side,
                positionSide=opposite_pos,
                type= 'STOP_MARKET',
                stopPrice=str(stop_loss),
                closePosition='true'
            )
            # Create a take profit order
            client.futures_create_order(
                symbol=symbol,
                side=opposite_side,
                positionSide=opposite_pos,
                type='TAKE_PROFIT_MARKET',
                stopPrice=str(take_profit),
                closePosition='true'
            )
            return order

        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def execute_trades(self):
        # Initialize the connection if there is not
        client = Client(api_key = api_key, api_secret = secret_key, tld = "com", testnet = True) #  testnet = True
        # print("WTH is happening0")

        for symbol in self.symbols:
            # print("WTH is happening1")
            atr, signal = self.define_strategy(symbol)
            if atr is None or signal is None:
                print(f"Skipping symbol '{symbol}' due to missing strategy data.")
                continue
            
            # print("WTH is happening2")

            ticker = client.futures_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            if price is None: continue

            logging.info(f'Symbol: {symbol}, Last Price:   {price}, ATR: {atr}, Signal: {signal}')
            print(f'Symbol: {symbol}, Last Price: {price}, ATR: {atr}, Signal: {signal}')

            if symbol == "ETHUSDT":
                self.units = 0.1
            else:
                self.units = 0.01

            if signal==2:
                sl = round(price - (self.sl_factor * atr), 2)
                tp = round(price + (self.tp_factor * atr), 2)
                # order = client.futures_create_order(symbol = self.symbol, side = "BUY", type = "MARKET", quantity = self.units)
                order = self.place_order(symbol, "BUY", "LONG", self.units, sl, tp)
                self.report_trade(order, "GOING LONG") 
            if signal==1:
                sl = round(price + (self.sl_factor * atr), 2)
                tp = round(price - (self.tp_factor * atr), 2)
                # order = client.futures_create_order(symbol = self.symbol, side = "SELL", type = "MARKET", quantity = self.units)
                order = self.place_order(symbol, "SELL", "SHORT", self.units, sl, tp)
                self.report_trade(order, "GOING SHORT")
            if signal==0:
                print(f"Trading signal = {signal}: No trade Quant, trying again in 5 mins")
        
    
    def report_trade(self, order, going): 
        # Initialize client
        client = Client(api_key=api_key, api_secret=secret_key, tld="com", testnet=True)

        if order is not None:
            for symbol in self.symbols:
                order_time = order["updateTime"]
                trades = client.futures_account_trades(symbol=symbol, startTime=order_time)
                order_time = pd.to_datetime(order_time, unit="ms")
                if not trades:
                    print(f"No trades data available for {symbol} at {order_time}.")
                    continue
                df = pd.DataFrame(trades)
                # Check if expected columns exist in DataFrame
                expected_columns = ["qty", "quoteQty", "commission", "realizedPnl"]
                if not all(column in df.columns for column in expected_columns):
                    print(f"Missing columns in trades data for {symbol} at {order_time}.")
                    continue

                # Convert columns to numeric
                for column in expected_columns:
                    df[column] = pd.to_numeric(df[column], errors="coerce")

                base_units = round(df.qty.sum(), 5)
                quote_units = round(df.quoteQty.sum(), 5)
                commission = -round(df.commission.sum(), 5)
                real_profit = round(df.realizedPnl.sum(), 5)
                price = round(quote_units / base_units, 5)
                # Calculate cumulative trading profits
                self.cum_profits += round((commission + real_profit), 5)
                # Print trade report
                print(2 * "\n" + 100 * "-")
                print(f"{order_time} | {going}") 
                print(f"{order_time} | Base_Units = {base_units} | Quote_Units = {quote_units} | Price = {price}")
                print(f"{order_time} | Profit = {real_profit} | CumProfits = {self.cum_profits}")
                print(100 * "-" + "\n")

if __name__ == "__main__":
    symbols = ["BTCUSDT", "ETHUSDT"] 
    last_action_timestamp = 0
    last_display_timestamp = 0
    trader = MysteryOfTheMissingHeart(symbols, units=0.01, leverage=5)
    while True:
        current_time = datetime.now()
        # Launch the algorithm
        current_timestamp = int(time.time())
        if (current_timestamp - last_action_timestamp) >= 300:
            start_time = time.time()
            # Account Info
            print("_______________________________________________________________________________________________________")
            print("BINANCE TESTNET ACCOUNT: MOTH SCALPING-101 STRATEGY")
            print("_______________________________________________________________________________________________________")
            print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("-------------------------------------------------------------------------------------------")
            # Look for trades
            trader.execute_trades()
            print("Open Positions:---------------------------------------------------------------------------------")
            execution_time = time.time() - start_time
            last_action_timestamp = int(time.time()) - (execution_time)