import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import time
import pandas_ta as ta

class MysteryOfTheMissingHeart:
    sl_factor = 1
    tp_factor = 1

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

    def get_hist_data(self, symbol, n_bars, timeframe=mt5.TIMEFRAME_M5): #changed timeframe
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

    def define_strategy(self, symbol):
        """    strategy-specifics      """
        # Initialize the connection if there is not
        mt5.initialize()
        
        symbol_df = self.get_hist_data(symbol, 500).dropna()
        if symbol_df.empty:
            print(f"Error: Historical data for symbol '{symbol}' is not available.")
            return None, None, None
        symbol_df.columns = [col.title() for col in symbol_df.columns]
        # Generate the signals based on the strategy rules
        symbol_df = self.generate_signal(symbol_df)

        #atr
        atr_series = ta.atr(symbol_df['High'], symbol_df['Low'], symbol_df['Close'], length=16)
        atr = atr_series.values[-1]
        
        #signal
        signal = symbol_df['signal'].values[-1]

        #logging plus debugging
        #print(f"Signals:   {symbol_df['Signal'].tail()}")
        return atr, signal, symbol_df['signal']

    def execute_trades(self):
        # Initialize the connection if there is not
        mt5.initialize()

        # signals_df = pd.DataFrame()
        for symbol in self.symbols:
            atr, signal, _ = self.define_strategy(symbol)
            # signals_df[f"{symbol}"] = signals
            if atr is None or signal is None:
                print(f"Skipping symbol '{symbol}' due to missing strategy data.")
                continue
            tick = mt5.symbol_info_tick(symbol)
            if tick is None: continue
            
            print(f'Symbol: {symbol}, Last Price: {tick.ask}, ATR: {atr}, Signal: {signal}')

            spread = abs(tick.bid-tick.ask)

            if signal==1:
               pass
            if signal==-1:
                pass
        
        # signals_df.to_csv("volatilitysignals_df.csv")

if __name__ == "__main__":
    symbols = ["Step Index", "Volatility 10 Index",  "Volatility 25 Index", "Volatility 50 Index", "Volatility 75 Index", "Volatility 100 Index"] 
    last_action_timestamp = 0
    last_display_timestamp = 0
    trader = MysteryOfTheMissingHeart(symbols)
    while True:
        current_time = datetime.now()
        # Launch the algorithm
        current_timestamp = int(time.time())
        if (current_timestamp - last_action_timestamp) >= 300:
            start_time = time.time()
            # Account Info
            if mt5.initialize():
                current_account_info = mt5.account_info()
                print("_______________________________________________________________________________________________________")
                print("DERIV DEMO ACCOUNT: COUNTERTREND SCALPING STRATEGY")
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