import time
from datetime import datetime
import logging
import os
from core.strategies.mean_reversion import MeanReversionTrader
from core.strategies.momentum import MomentumTrader
from core.strategies.scalping import ScalpingTrader
from core.config import get_broker_config, get_strategy_config, SYMBOL_CONFIGS

def run_strategy(strategy_name: str, broker_name: str, symbol_type: str):
    # Set up logging
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f'{strategy_name}.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
    )

    broker_config = get_broker_config(broker_name)
    strategy_config = get_strategy_config(strategy_name)
    symbols = SYMBOL_CONFIGS.get(symbol_type, [])

    if not symbols:
        logging.error(f"No symbols configured for {symbol_type}")
        return

    # Initialize the appropriate strategy
    try:
        if strategy_name == 'mean_reversion':
            trader = MeanReversionTrader(symbols=symbols, **strategy_config)
        elif strategy_name == 'momentum':
            trader = MomentumTrader(symbols=symbols, **strategy_config)
        elif strategy_name == 'scalping':
            trader = ScalpingTrader(symbols=symbols, **strategy_config)
        else:
            logging.error(f"Unknown strategy: {strategy_name}")
            return

        trader.initialize_mt5(**broker_config)
        logging.info(f"Starting {strategy_name} strategy on {symbol_type} with {broker_name}")
        
        # Main trading loop
        while True:
            try:
                trader.execute_trades()
                time.sleep(1)  # 1 second delay between iterations
            except Exception as e:
                logging.error(f"Error in trading loop: {e}")
                time.sleep(5)  # Longer delay on error
                continue

    except KeyboardInterrupt:
        logging.info(f"{strategy_name} stopped by user")
    except Exception as e:
        logging.error(f"{strategy_name} failed: {e}")

if __name__ == "__main__":
    # Example usage - modify these values as needed
    strategy_name = 'scalping'  # or 'momentum' or 'mean_reversion'
    broker_name = 'FTMO'       # or 'Oanda' or 'Exness'
    symbol_type = 'forex'      # or 'indices' or 'crypto'
    
    run_strategy(strategy_name, broker_name, symbol_type)