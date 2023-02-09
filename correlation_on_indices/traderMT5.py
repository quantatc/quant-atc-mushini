from turtle import position
import warnings
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import MetaTrader5 as mt5
import talib
from dotenv import load_dotenv
import os
#from sympy import symbols
import time
warnings.filterwarnings("ignore")

#Tozvitangidza hedu zve ehe quant chii chii
load_dotenv()

# Load environment variables
mt_login_id = int(os.getenv("mt_login_id"))
mt_password = os.getenv("mt_password")
mt_server_name = os.getenv("mt_server_name")

if not mt_login_id or not mt_password or not mt_server_name:
    raise ValueError("Please set the environment variables METATRADER_LOGIN_ID, METATRADER_PASSWORD and METATRADER_SERVER")

class MT5Trader:
    def __init__(self, symbols, lot_size):

        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name, password=mt_password)

        self.symbols = symbols  #list of symbols
        self.lot = lot_size
        self.order_result_comment = None
        self.pos_summary = None
        self.Invested = False

        #***************Strategy Attributes*********************************************************
        self.ger30 = np.array([])
        #*******************************************************************************************

    def get_hist_data(self, symbol, n_bars, timeframe=mt5.TIMEFRAME_H1): #changed timframe
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
        data = data["close"].to_frame()
        #data.rename(columns = {'close' : str(symbol)}, inplace = True)
        #appended_data.append(data)
        
        #self.data = pd.concat(appended_data, axis=0)
        return data

    def orders(self, symbol):
        """ Function to Send the orders """
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name,password=mt_password)

        # **************************** Open a trade *****************************************************************
        tick = mt5.symbol_info_tick(symbol)
        symbol_info = mt5.symbol_info(symbol)

        # if the symbol is unavailable in MarketWatch, add it
        if not symbol_info.visible:
            print(symbol, "is not visible, trying to switch on")
            if not mt5.symbol_select(symbol,True):
                print("symbol_select({}}) failed, exit",symbol)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": self.lot,
            "type": mt5.ORDER_TYPE_BUY,
            "price": tick.ask,
            "deviation": 20,
            "magic": 222222,
            "comment": "correlation algo order",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        # send a trading request
        self.result = mt5.order_send(request)
        if self.result.retcode != mt5.TRADE_RETCODE_DONE:
            print("order_send failed, retcode={}".format(self.result.retcode))
            # request the result as a dictionary and display it element by element
            result_dict=self.result._asdict()
            for field in result_dict.keys():
                print("   {}={}".format(field,result_dict[field]))
                # if this is a trading request structure, display it element by element as well
                if field=="request":
                    traderequest_dict=result_dict[field]._asdict()
                    for tradereq_filed in traderequest_dict:
                        print("       traderequest: {}={}".format(tradereq_filed,traderequest_dict[tradereq_filed]))

        self.order_result_comment = self.result.comment

    def close_positions(self, position):
        """ Function to close all positions """
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name,password=mt_password)

        tick = mt5.symbol_info_tick(position.symbol)
        request = {
               "action": mt5.TRADE_ACTION_DEAL,
               "symbol": position.symbol,
               "volume": position.volume,
               "type": mt5.ORDER_TYPE_BUY if position.type == 1 else mt5.ORDER_TYPE_SELL,
               "position": position.ticket,
               "price": tick.ask if position.type == 1 else tick.bid,
               "deviation": 20,
               "magic": 222222,
               "comment": "correlation algo order",
               "type_time": mt5.ORDER_TIME_GTC,
               "type_filling": mt5.ORDER_FILLING_FOK,
           }
        # send a trading request
        self.res = mt5.order_send(request)
        print(f"CLOSE LONG TRADE: {self.res}")

    def define_strategy(self):
        """    strategy-specifics      """
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name,password=mt_password)
        
        us30 = self.get_hist_data(self.symbols[0], 14).dropna()
        ger30 = self.get_hist_data(self.symbols[1], 14).dropna()
        nas100 = self.get_hist_data(self.symbols[2], 14).dropna()

        #momentum indicator filtering
        self.ger30 = np.append(self.ger30, ger30)
        mom = talib.MOM(self.ger30, timeperiod=3)
        self.lastmom = mom[-1]
        
        x_prices = us30.to_numpy()
        y_prices = ger30.to_numpy()
        z_prices = nas100.to_numpy()

        if len(x_prices) != len(y_prices): return
        self.corr, _ = spearmanr(x_prices, y_prices)
        self.corr2, _ = spearmanr(z_prices, y_prices)

        #return self.corr, self.corr2, self.lastmom

    def execute_trades(self):
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name,password=mt_password)
        self.define_strategy()
        # check if we are invested
        positions_total = mt5.positions_total()
        positions = mt5.positions_get()
        us30_positions = mt5.positions_get(symbol=self.symbols[0])
        ger30_positions = mt5.positions_get(symbol=self.symbols[1])
        nas100_positions = mt5.positions_get(symbol=self.symbols[2])

        if positions_total > 0: 
            self.Invested = True

        #if not self.Invested:
        #if self.lastmom > 0:
        if self.corr > -0.4 and self.corr < 0.4:
            if len(us30_positions) == 0:
                self.orders(self.symbols[0])
                print(f"OPEN LONG TRADE: {self.result}")
            if len(ger30_positions) == 0:    
                self.orders(self.symbols[1])
                print(f"OPEN LONG TRADE: {self.result}")           
        if self.corr2 > -0.4 and self.corr2 < 0.4:
            if len(nas100_positions) == 0:
                self.orders(self.symbols[2])
                print(f"OPEN LONG TRADE: {self.result}")

        elif self.Invested:
            for position in positions:
                if self.corr > 0.9:
                    self.close_positions(position)
                if self.corr < -0.9:
                    self.close_positions(position)
    
    def display_correlation(self):
        # Initialize the connection if there is not
        mt5.initialize(login=mt_login_id, server=mt_server_name,password=mt_password)
        self.define_strategy()

        # check if we are invested
        positions_total = mt5.positions_total()
        
        us30_positions = mt5.positions_get(symbol=self.symbols[0])
        ger30_positions = mt5.positions_get(symbol=self.symbols[1])
        nas100_positions = mt5.positions_get(symbol=self.symbols[2])

        
        print("-"*80)
        print(f"Open Positions: {positions_total}")

        if positions_total > 0:
            print(f"US30: {len(us30_positions)}")
            print(f"US100: {len(nas100_positions)}")
            print(f"GER30: {len(ger30_positions)}")
        

        print("\nCorrelations:")
        print(f"Corr: {self.corr}    Corr2: {self.corr2}")
        print(f"Momentum:   {self.lastmom}")
        print("-"*80)

if __name__ == "__main__":

    #symbols = ['US30.cash', 'GER40.cash', 'US100.cash']
    #symbols = ['US30', 'DE30', 'US100']
    symbols = ['DJI30', 'DAX40', 'NQ100']

    last_action_timestamp = 0
    last_display_timestamp = 0

    trader = MT5Trader(symbols=symbols, lot_size=2.5)

    while True:

        # Launch the algorithm
        current_timestamp = int(time.time())

        if (current_timestamp - last_action_timestamp) > 60: #changed to 60 from 3600

            if datetime.now().weekday() not in (5,6):
                
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
        
        if (current_timestamp - last_display_timestamp) > 60:

            trader.display_correlation()

            last_display_timestamp = int(time.time())

