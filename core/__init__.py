"""
Core package for the Quant ATC Trading System.
"""

from .base_trader import BaseTrader
from .config import STRATEGY_CONFIGS
from .utils import *

__all__ = ['BaseTrader', 'STRATEGY_CONFIGS']