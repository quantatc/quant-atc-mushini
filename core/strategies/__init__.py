"""
Strategy implementations for the Quant ATC Trading System.
"""

from .mean_reversion import MeanReversionStrategy
from .momentum import MomentumStrategy
from .scalping import ScalpingStrategy

__all__ = ['MeanReversionStrategy', 'MomentumStrategy', 'ScalpingStrategy']