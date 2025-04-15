import time
from datetime import datetime
import logging
import os
from multiprocessing import Process, Manager
from core.strategies.mean_reversion import MeanReversionTrader
from core.strategies.momentum import MomentumTrader
from core.strategies.scalping import ScalpingTrader
from core.config import get_broker_config, get_strategy_config, SYMBOL_CONFIGS

# Global dictionary to keep track of running strategy processes
strategy_processes = {}
manager = Manager()
strategy_status = manager.dict()

def run_strategy(strategy_name: str, broker_name: str, symbol_type: str, status_dict=None):
    # Set up per-strategy log file
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
        if status_dict is not None:
            status_dict[strategy_name] = 'error'
        return

    if strategy_name == 'mean_reversion':
        trader = MeanReversionTrader(symbols=symbols, **strategy_config)
    elif strategy_name == 'momentum':
        trader = MomentumTrader(symbols=symbols, **strategy_config)
    elif strategy_name == 'scalping':
        trader = ScalpingTrader(symbols=symbols, **strategy_config)
    else:
        logging.error(f"Unknown strategy: {strategy_name}")
        if status_dict is not None:
            status_dict[strategy_name] = 'error'
        return

    trader.initialize_mt5(**broker_config)
    last_check = 0
    check_interval = 60
    if status_dict is not None:
        status_dict[strategy_name] = 'running'
    try:
        while True:
            current_time = time.time()
            if current_time - last_check >= check_interval:
                try:
                    trader.execute_trades()
                    last_check = current_time
                except Exception as e:
                    logging.error(f"Error in trading loop: {e}")
                    time.sleep(5)
                    continue
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info(f"{strategy_name} stopped by user")
    except Exception as e:
        logging.error(f"{strategy_name} failed: {e}")
    finally:
        if status_dict is not None:
            status_dict[strategy_name] = 'stopped'

def start_strategy_process(strategy_name, broker_name, symbol_type):
    if strategy_name in strategy_processes and strategy_processes[strategy_name].is_alive():
        return False  # Already running
    p = Process(target=run_strategy, args=(strategy_name, broker_name, symbol_type, strategy_status))
    p.start()
    strategy_processes[strategy_name] = p
    strategy_status[strategy_name] = 'running'
    return True

def stop_strategy_process(strategy_name):
    p = strategy_processes.get(strategy_name)
    if p and p.is_alive():
        p.terminate()
        p.join()
        strategy_status[strategy_name] = 'stopped'
        return True
    return False

def get_strategy_status(strategy_name):
    return strategy_status.get(strategy_name, 'stopped')

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    # Example usage
    strategy_name = 'scalping'
    broker_name = 'FTMO'
    symbol_type = 'forex'
    try:
        run_strategy(strategy_name, broker_name, symbol_type)
    except KeyboardInterrupt:
        logging.info("Strategy execution stopped by user")
    except Exception as e:
        logging.error(f"Strategy execution failed: {e}")