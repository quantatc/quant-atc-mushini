from turtle import position
import warnings
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import MetaTrader5 as mt5
import talib
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
import os
#from sympy import symbols
from time import sleep
import time
warnings.filterwarnings("ignore")

load_dotenv()


# Load environment variables
live_trading = int(os.getenv("LIVE_TRADING_FAS"))

if live_trading == 1:
    mt_login_id = int(os.getenv("METATRADER_LOGIN_ID_PROD"))
    mt_password = os.getenv("METATRADER_PASSWORD_PROD")
    mt_server_name = os.getenv("METATRADER_SERVER_PROD")

else:
    mt_login_id = int(os.getenv("METATRADER_LOGIN_ID_DEMO"))
    mt_password = os.getenv("METATRADER_PASSWORD_DEMO")
    mt_server_name = os.getenv("METATRADER_SERVER_DEMO")


# Setup for Sentry
environment='prod' if live_trading == 1 else 'demo'

sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    integrations=[FlaskIntegration()],
    traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE')),
    environment=environment,
)


if not mt_login_id or not mt_password or not mt_server_name:
    raise ValueError("Please set the environment variables METATRADER_LOGIN_ID, METATRADER_PASSWORD and METATRADER_SERVER")


class MT5Trader:
    def __init__(self, symbols, lot):
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name, password=mt_password)

        self.symbols = symbols  #list of symbols
        self.lot_size = lot
        self.Invested = False
        #self.lot = lot_size
        self.order_result_comment = None
        self.pos_summary = None

        #***************Strategy Attributes*********************************************************
        self.his_period = 6*20
        self.sl_factor = 4
        self.tp_factor = 1
        self.ema_period = 20
        self.fri_period = 14
        self.atr_period = 14
        self.rsi_period = 2
        self.rsi_lower_thresold = 20
        self.rsi_upper_thresold = 80
        self.rsi_close_buy = 90
        self.rsi_close_sell = 10
        #*******************************************************************************************

    def get_hist_data(self, symbol, n_bars, timeframe=mt5.TIMEFRAME_H1):
        """ Function to import the data of the chosen symbol"""
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name, password=mt_password)

        #get data and convert it into pandas dataframe
        utc_from = datetime.now()
        rates = mt5.copy_rates_from(symbol, timeframe, utc_from, n_bars)
        data = pd.DataFrame(rates)
        data['time'] = pd.to_datetime(data['time'], unit='s')
        data['time'] = pd.to_datetime(data['time'], format='%Y-%m-%d')
        data = data.set_index('time')
        #data = data.to_frame()
        #data.rename(columns = {'close' : str(symbol)}, inplace = True)
        #appended_data.append(data)
        
        #self.data = pd.concat(appended_data, axis=0)
        return data

    def orders(self, symbol, lot_size, stop_loss, take_profit, buy=True, id_position =None):
        """ Function to Send the orders """
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name, password=mt_password)

        # **************************** Open a trade *****************************************************************
        tick = mt5.symbol_info_tick(symbol)
        symbol_info = mt5.symbol_info(symbol)
        # Get filling mode
        filling_mode = symbol_info.filling_mode - 1

        if not symbol_info.visible:
            mt5.symbol_select(symbol, True)

        # **************************** Open a trade *****************************
        if id_position == None:

            if buy:
                type_trade = mt5.ORDER_TYPE_BUY
                price = tick.ask
            # Sell order Parameters
            else:
                type_trade = mt5.ORDER_TYPE_SELL
                price = tick.bid

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot_size,
                "type": type_trade,
                "price": price,
                "sl": stop_loss,
                "tp": take_profit,
                "deviation": 20,
                "magic": 115765,
                "comment": "fractical_analysis algo order",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }

            # send a trading request
            self.result = mt5.order_send(request)
            self.order_result_comment = self.result.comment

        # **************************** Close a trade *****************************
        else:
            # Buy order Parameters
            if buy:
                type_trade = mt5.ORDER_TYPE_SELL
                price = tick.bid

            # Sell order Parameters
            else:
                type_trade = mt5.ORDER_TYPE_BUY
                price = tick.ask

            # Close the trade
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot_size,
                "type": type_trade,
                "position": id_position,
                "price": price,
                "deviation": 20,
                "magic": 115765,
                "comment": "fractical_analysis algo order",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }

            # send a trading request
            self.result = mt5.order_send(request)
            self.order_result_comment = self.result.comment

    def resume(self):
      """ Return the current positions. Position=0 --> Buy """
      # Initialize the connection if there is not
      mt5.initialize(login=mt_login_id, server=mt_server_name, password=mt_password)

      # Define the name of the columns that we will create
      colonnes = ["ticket", "position", "symbol", "volume"]

      # Go take the current open trades
      current = mt5.positions_get()

      # Create a empty dataframe
      summary = pd.DataFrame()

      # Loop to add each row in dataframe
      # (Can be ameliorate using of list of list)
      for element in current:
           element_pandas = pd.DataFrame([element.ticket,
                                          element.type,
                                          element.symbol,
                                          element.volume],
                                         index=colonnes).transpose()
           summary = pd.concat((summary, element_pandas), axis=0)

      return summary


    def define_strategy(self):
        """    strategy-specifics      """
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name, password=mt_password)

        self.indicator_values = {}

        for symbol in self.symbols:
            raw = self.get_hist_data(symbol, self.his_period).dropna()
            raw.dropna(inplace=True)
            #indicator values
            true_range = talib.ATR(raw.high.values, raw.low.values, raw.close.values, timeperiod=self.atr_period)
            rsi = talib.RSI(raw.close, timeperiod = self.rsi_period)
            raw['emaHigh'] = raw.high.ewm(span=self.ema_period, adjust=False).mean()
            raw['emaLow'] = raw.low.ewm(span=self.ema_period, adjust=False).mean()
            raw['highDiff'] = raw.high - raw.emaHigh
            raw['lowDiff'] = raw.low - raw.emaLow
            raw['stdHigh'] = raw.high.rolling(self.ema_period).std()
            raw['stdLow'] = raw.low.rolling(self.ema_period).std()

            max = raw['highDiff'].iloc[-self.fri_period:].max()
            min = raw['lowDiff'].iloc[-self.fri_period:].min()

            fractical = (max - min)/ ((raw['stdHigh'].iloc[-1] + raw['stdLow'].iloc[-1])/2)
            print(f"Fractical:   {fractical}")
            print(f"RSI:   {rsi[-1]}")
            print(f"ATR:   {true_range[-1]}")
            
            #results order: fractical, current rsi, ATR
            self.indicator_values[symbol] = [fractical, rsi[-1], true_range[-1]]


    def execute_trades(self):
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name, password=mt_password)
        long = False
        short = False

        self.define_strategy()
        #results order: fractical, current rsi, ATR
        
        
        for symbol in self.symbols:
            symbol_info = mt5.symbol_info(symbol)

            if not symbol_info.visible:
                mt5.symbol_select(symbol, True)

            fract = self.indicator_values[symbol][0]
            rsi = self.indicator_values[symbol][1]
            atr = self.indicator_values[symbol][2]

            tick = mt5.symbol_info_tick(symbol)
            # check if we are invested
            positions_total = mt5.positions_total()
            if positions_total > 0: 
                self.Invested = True
            positions = mt5.positions_get()
            position = mt5.positions_get(symbol=symbol)
            #print(f"Lot: {lot_size}")

            if (len(position) == 0 and fract <= 1.1 and rsi < self.rsi_lower_thresold):
                min_stop = round(tick.ask - self.sl_factor * atr, 5)
                target_profit = round(tick.ask + self.tp_factor * atr, 5)
                long = True
                self.orders(symbol, self.lot_size, min_stop, target_profit, buy=True)
                print(f"OPEN LONG TRADE: {self.result}")

            elif (len(position) == 0 and fract <= 1.1 and rsi > self.rsi_upper_thresold):
                min_stop = round(tick.bid + self.sl_factor * atr, 5)
                target_profit = round(tick.bid - self.tp_factor * atr, 5)
                short = True
                self.orders(symbol, self.lot_size, min_stop, target_profit, buy=False)
                print(f"OPEN SHORT TRADE: {self.result}")

            # Initialize the device
            current_open_positions = self.resume()
            try:
                identifier = current_open_positions.loc[current_open_positions["symbol"]==symbol].values[0][0]
                pos = current_open_positions.loc[current_open_positions["symbol"]==symbol].values[0][1]
            except:
                identifier = None
                pos = None

            print(f"POSITION: {pos} \t ID: {identifier}")
            if long==True and pos==0:
                long=False

            #if self.Invested:
            elif long==False and pos==0:
                if rsi > self.rsi_close_buy:
                    self.orders(symbol, self.lot_size, None, None, buy=True, id_position=identifier)
                    print(f"CLOSE LONG TRADE: {self.result}")
            
            elif short==True and pos == 0:
                short=False
            
            elif short == False and pos == 1:
                if rsi < self.rsi_close_sell:
                    self.orders(symbol, self.lot_size, None, None, buy=False, id_position=identifier)
                    print(f"CLOSE SHORT TRADE: {self.result}")
            
            else:
                pass

    def display_positions(self):
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name,password=mt_password)
        self.define_strategy()

        # check if we are invested
        positions_total = mt5.positions_total()

        print("-"*80)
        print(f"Open Positions: {positions_total}")

        for symbol in self.symbols:
            symbol_positions = mt5.positions_get(symbol=symbol)

            if positions_total > 0:
                print(symbol + ": " + f"{len(symbol_positions)}")
        
        print("-"*80)       
            

if __name__ == "__main__":

    symbols = ['EURUSD', 'AUDNZD', 'GBPNZD'] 

    last_action_timestamp = 0
    last_display_timestamp = 0

    execute_trade_interval = 3600  #3600 * 4 # every 4 hours
    display_position_interval = 1800 #3600  # every 1 hour

    trader = MT5Trader(symbols= symbols, lot=0.01)

    while True:

        # Launch the algorithm
        current_timestamp = int(time.time())

        if (current_timestamp - last_action_timestamp) > execute_trade_interval:

            if datetime.now().weekday() not in (5,6):
                
                # Initialize the connection if there is not
                mt5.initialize(login=mt_login_id, server=mt_server_name,password=mt_password)

                # Account Info
                current_account_info = mt5.account_info()
                print("------------------------------------------------------------------------------------------")
                print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Balance: {current_account_info.balance} USD,\t"
                    f"Equity: {current_account_info.equity} USD, \t"
                    f"Profit: {current_account_info.profit} USD")
                print("-------------------------------------------------------------------------------------------")
                
                # Close all trades
                trader.execute_trades()

            last_action_timestamp = int(time.time())
        
        if (current_timestamp - last_display_timestamp) > display_position_interval:

            trader.display_positions()

            last_display_timestamp = int(time.time())


        # to avoid excessive cpu usage because loop running lightning fast
        sleep(30)