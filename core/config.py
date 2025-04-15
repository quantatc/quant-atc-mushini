from typing import Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

# Broker configurations
BROKER_CONFIGS = {
    'FTMO': {
        'login': int(os.getenv('mt_login_id3', 0)),
        'password': os.getenv('mt_password3', ''),
        'server': os.getenv('mt_server_name3', ''),
        'path': os.getenv('path3', '')
    },
    'Oanda': {
        'login': int(os.getenv('mt_login_idOANDA', 0)),
        'password': os.getenv('mt_passwordOANDA', ''),
        'server': os.getenv('mt_server_nameOANDA', ''),
        'path': os.getenv('pathOANDA', '')
    },
    'Exness': {
        'login': int(os.getenv('mt_login_id5', 0)),
        'password': os.getenv('mt_password5', ''),
        'server': os.getenv('mt_server_name5', ''),
        'path': os.getenv('path5', '')
    }
}

# Strategy configurations
STRATEGY_CONFIGS = {
    'mean_reversion': {
        'risk_pct': 0.01,
        'sl_factor': 1.5,
        'tp_factor': 2.0,
        'z_threshold': 2.0,
        'atr_period': 14,
        'ma_period': 20
    },
    'momentum': {
        'risk_pct': 0.01,
        'sl_factor': 1.5,
        'tp_factor': 2.0,
        'fast_ma': 20,
        'slow_ma': 50,
        'atr_period': 14
    },
    'scalping': {
        'risk_pct': 0.01,
        'sl_factor': 1.5,
        'tp_factor': 1.0,
        'rsi_period': 14,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'atr_period': 14,
        'atr_threshold': 0.0002  # Minimum volatility threshold
    }
}

# Symbol configurations
SYMBOL_CONFIGS = {
    'forex': ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF'],
    'indices': ['US100', 'GER40', 'US30'],
    'crypto': ['BTCUSD', 'ETHUSD']
}

# Timeframe configurations
TIMEFRAME_CONFIGS = {
    'scalping': 'M5',
    'intraday': 'H1',
    'swing': 'D1'
}

def get_broker_config(broker_name: str) -> Dict[str, Any]:
    """Get broker configuration"""
    return BROKER_CONFIGS.get(broker_name, {})

def get_strategy_config(strategy_name: str) -> Dict[str, Any]:
    """Get strategy configuration"""
    return STRATEGY_CONFIGS.get(strategy_name, {})