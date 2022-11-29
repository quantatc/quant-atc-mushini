from multiprocessing.util import get_logger
import warnings
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import talib
from tqdm import tqdm
import logging
import math
from scipy import stats as st
from statistics import mean
from dotenv import load_dotenv
import os
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import APIError
from iexfinance.stocks import Stock
from iexfinance.stocks import get_historical_data, get_historical_intraday
from vasof_indicator import *
#from sympy import symbols
import time
warnings.filterwarnings("ignore")

# logging.basicConfig(format='%(asctime)s:: %(message)s \n', level=logging.INFO)

load_dotenv()

endpoint = os.getenv('ALPACA_ENDPOINT')
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')
IEX_TOKEN = os.getenv('IEX_TOKEN')

class AlpacaTrader:
    def __init__(self, symbols):

        # Initialize the connection if there is not
        api = tradeapi.REST(api_key, secret_key, endpoint)

        self.symbols = symbols  #list of symbols
        #self.qty = lot_size
        self.order_result_comment = None
        self.pos_summary = None
        self.Invested = False

        #***************Strategy Attributes*********************************************************
        self.window = 2
        self.start = datetime(2022, 1, 1)
        self.atr_period = 50
        self.sl_factor = 1.5
        self.tp_factor = 1
        self.lowerThres = 20
        self.upperThres = 90
        #*******************************************************************************************
    def get_hist_data(self, symbol, start, fib_period=20):
        """ Function to import the data of the chosen symbol"""
        # Initialize the connection if there is not
        df = get_historical_data(symbol, start, token=IEX_TOKEN)
        #df = get_historical_intraday(symbol, date=start, output_format='pandas')
        df = df[['uOpen', 'uHigh', 'uLow', 'uClose']]
        df.rename(columns = {'uOpen':'Open', 'uHigh':'High', 'uLow':'Low', 'uClose':'Close'}, inplace=True)
        df.dropna(inplace=True)
        #df = df.loc[start:end]
        df.reset_index(inplace = True)
        my_data = np.array(df)
        my_data = adder(my_data, 3)
        my_data = fib_stoch(my_data, fib_period, 4, 5)
        df = pd.DataFrame(my_data, columns = ["Date", "Open", "High", "Low", "Close", "std", "nstd", "fib_stoch"])
        df.set_index("Date", inplace = True)
        df.index = pd.to_datetime(df.index)
        df = df.apply(pd.to_numeric)
        df = df.drop(columns = ["std", "nstd"])
        return df

    def orders(self, symbol, quantity, tp, sl):
        """ Function to Send the orders """
        # Initialize the connection if there is not
        api = tradeapi.REST(api_key, secret_key, endpoint)

        # **************************** Open a trade *****************************************************************
        order = api.submit_order(
            symbol=symbol,
            side='buy',
            type='market',
            qty=quantity,
            time_in_force='day',
            order_class='bracket',
            take_profit=dict(
                limit_price=str(tp),
            ),
            stop_loss=dict(
                stop_price=str(sl),
            ))
        
        return order

    def close_positions(self, symbol):
        """ Function to close positions by symbol """
        # Initialize the connection if there is not
        api = tradeapi.REST(api_key, secret_key, endpoint)
        # send a close all request
        res = api.close_position(symbol)
        print(res)

    def define_strategy(self):
        """    strategy-specifics      """
        self.strategy_values = {}

        for symbol in self.symbols:
            try:
                df = self.get_hist_data(symbol, self.start, fib_period=self.window)
                #indicator values
                print("-"*80)
                print(f'{symbol}:  STRATEGY VALUES')
                true_range = talib.ATR(df.High.values, df.Low.values, df.Close.values, timeperiod=self.atr_period)
                #print(f"ATR:   {true_range[-1]}")
                vasof = df.fib_stoch.values[-1]
                prev_vasof = df.fib_stoch.values[-2]
                print(f"Momentum:   {vasof}        Previous Momentum: {prev_vasof}")
                print("-"*80)
                
                #results order: vasof, prev_vasof, ATR
                self.strategy_values[symbol] = [vasof, prev_vasof, true_range[-1]]
            except AssertionError as msg:
                print(msg)

    def execute_trades(self):
        # Initialize the connection if there is not
        api = tradeapi.REST(api_key, secret_key, endpoint)
        self.define_strategy()
        # check if we are invested

        position_size = api.get_account()._raw['equity']
        position_size = float(position_size)/ len(self.symbols)

        for symbol in self.symbols:
            try:
                position = api.get_position(symbol)
            except APIError:
                position = None
            
            symbol_obj = Stock(symbol, token=IEX_TOKEN)
            quote = symbol_obj.get_quote()
            price = quote['latestPrice'].values[0]
            quantity = math.ceil(position_size/ price)
            #results order from define_strategy: vasof, prev_vasof, ATR
            vasof = self.strategy_values[symbol][0]
            prev_vasof = self.strategy_values[symbol][1]
            atr = self.strategy_values[symbol][2]

            #if not self.Invested:
            if position == None:
                if vasof <= self.lowerThres and prev_vasof > self.lowerThres:
                    min_stop = round(price - self.sl_factor * atr, 2)
                    target_profit = round(price + self.tp_factor * atr, 2)
                    res = self.orders(symbol, quantity, target_profit, min_stop)
                    print(f"OPEN LONG TRADE: {res}")

            elif position != None:
                if vasof > self.upperThres:
                    self.close_positions(symbol)
    
    def display_positions(self):
        # Initialize the connection if there is not
        api = tradeapi.REST(api_key, secret_key, endpoint)
        self.define_strategy()

        # Account Info
        current_account_info = api.get_account()._raw
        print("------------------------------------------------------------------------------------------")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Cash: {current_account_info['cash']} USD,\t"
            f"Equity: {current_account_info['equity']} USD, \t"
            f"Long Market Value: {current_account_info['long_market_value']} USD")
        print("-------------------------------------------------------------------------------------------")

        # check if we are invested
        positions_total = len(api.list_positions())

        print("-"*80)
        print(f"Open Positions: {positions_total}")

        if positions_total > 0:
            positions = api.list_positions()
            pos_symbols = [pos._raw['symbol'] for pos in positions]
            for symbol in self.symbols:
                if symbol in pos_symbols:
                    print(f"{symbol}: {1}")
                else:
                    print(f"{symbol}: {0}")

        print("-"*80)

class UniverseSelector:
    def __init__(self, shariah_symbols_dir):
        self.shariah_dir = shariah_symbols_dir
        self.wiki = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'

    def universe_selection(self):
        """ Function that runs once a month to select stocks that have the highest momentum """
        # Scrape the entire S&P500 list from Wikipedia into a Pandas DataFrame;
        ticker_list = pd.read_html(self.wiki)
        sp500_tickers = ticker_list[0].Symbol
        all_stocks = pd.read_csv(self.shariah_dir)#'shariah_symbols_supported.csv'
        all_stocks = list(all_stocks.symbol)
        sp_shariah_tickers = [ticker for ticker in list(sp500_tickers) if ticker in all_stocks]
        hqm_columns = [
                'Ticker', 
                'Price', 
                'One-Year Price Return', 
                'One-Year Return Percentile',
                'Six-Month Price Return',
                'Six-Month Return Percentile',
                'Three-Month Price Return',
                'Three-Month Return Percentile',
                'One-Month Price Return',
                'One-Month Return Percentile',
                'One-Week Price Return',
                'One-Week Return Percentile',
                '50-200-Moving-Average Price Return',
                '50-200-Moving-Average Return Percentile',
                'HQM Score'
                ]
        hqm_list = []
        for symbol in tqdm(list(sp_shariah_tickers)):
            symbol_obj = Stock(symbol, token=IEX_TOKEN)
            quote = symbol_obj.get_quote()
            stats = symbol_obj.get_key_stats()
            price = quote['latestPrice'].values[0]
            ma50 = stats['day50MovingAvg'].values[0]
            ma200 = stats['day200MovingAvg'].values[0]
            #print(symbol, " : ",price)
            if price > 0 and ma200 > 0:
                ma_pct_change = round((ma50 - ma200)/ ma200, 4)
                #print(symbol, " : ",ma_pct_change)
                hqm_dataframe = hqm_list.append([symbol, 
                                                price,
                                                stats['year1ChangePercent'].values[0],
                                                'N/A',
                                                stats['month6ChangePercent'].values[0],
                                                'N/A',
                                                stats['month3ChangePercent'].values[0],
                                                'N/A',
                                                stats['month1ChangePercent'].values[0],
                                                'N/A',
                                                stats['day5ChangePercent'].values[0],
                                                'N/A',
                                                ma_pct_change,
                                                'N/A',
                                                'N/A'])
        hqm_dataframe = pd.DataFrame(hqm_list, columns = hqm_columns)
        
        #Calulate percintal scores for all the features
        time_periods = [
                'One-Year',
                'Six-Month',
                'Three-Month',
                'One-Month',
                'One-Week',
                '50-200-Moving-Average'
                ]

        for row in hqm_dataframe.index:
            for time_period in time_periods:
                hqm_dataframe.loc[row, f'{time_period} Return Percentile'] = st.percentileofscore(hqm_dataframe[f'{time_period} Price Return'],
                hqm_dataframe.loc[row, f'{time_period} Price Return'])/100
        
        #Calculate HQM Score
        for row in hqm_dataframe.index:
            momentum_percentiles = []
            for time_period in time_periods:
                momentum_percentiles.append(hqm_dataframe.loc[row, f'{time_period} Return Percentile'])
            hqm_dataframe.loc[row, 'HQM Score'] = mean(momentum_percentiles)
        
        #Sorting dataframe
        hqm_dataframe_sorted = hqm_dataframe.sort_values(by = 'HQM Score', ascending = False)
        sorted_list = list(hqm_dataframe_sorted.Ticker)

        return sorted_list

if __name__ == "__main__":
    #symbols = selector.universe_selection()
    symbols = pd.read_csv('C:\work\mt5-trading-strategy\momentum_shariah_stock_trader\sp_shariah_sorted_stocks.csv')
    symbols = list(symbols.Ticker)[:51]

    last_action_timestamp = 0
    last_display_timestamp = 0
    execute_trade_interval = 3600  #3600 * 3 every 3 hours
    display_position_interval = 1800 #1800 every 30 mins

    trader = AlpacaTrader(symbols=symbols)

    while True:
        #establish connection
        api = tradeapi.REST(api_key, secret_key, endpoint)
        # Launch the algorithm
        current_timestamp = int(time.time())
        #Check if the market is open
        market_open = api.get_clock()._raw
        next_open = market_open['next_open']

        if (current_timestamp - last_action_timestamp) > execute_trade_interval:

            if market_open['is_open'] == True:            
                # execute trades
                trader.execute_trades()

            else:
                print('Market is closed...' + f'Next open time is {next_open} New York Time')

            last_action_timestamp = int(time.time())
        
        if (current_timestamp - last_display_timestamp) > display_position_interval:

            trader.display_positions()

            last_display_timestamp = int(time.time())

        current_date = datetime.utcnow()
        if current_date.weekday() == 0 and current_date.hour == 12 and current_date.minute == 0:
            selector = UniverseSelector('C:\work\mt5-trading-strategy\momentum_shariah_stock_trader\shariah_symbols_supported.csv')
            symbols = selector.universe_selection()
            symbols = symbols[:51]
        
        time.sleep(45)
