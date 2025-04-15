# Quant ATC Trading System

A modular trading system supporting multiple strategies and brokers.

## Getting Started

### Setting up the Development Environment

1. Create a Python virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:

   - On Windows (PowerShell):
   ```bash
   Set-ExecutionPolicy RemoteSigned -Scope Process
   .\venv\Scripts\activate
   ```
   
   - On Windows (Command Prompt):
   ```bash
   venv\Scripts\activate.bat
   ```
   
   - On Unix or MacOS:
   ```bash
   source venv/bin/activate
   ```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install the package in development mode:
```bash
pip install -e .
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your broker credentials:
```env
# FTMO
mt_login_id3=your_login
mt_password3=your_password
mt_server_name3=your_server
path3=path_to_mt5

# Oanda
mt_login_idOANDA=your_login
mt_passwordOANDA=your_password
mt_server_nameOANDA=your_server
pathOANDA=path_to_mt5

# Exness
mt_login_id5=your_login
mt_password5=your_password
mt_server_name5=your_server
path5=path_to_mt5
```

## Available Strategies

### Mean Reversion
- Uses Z-score to identify overbought/oversold conditions
- ATR-based position sizing and stop loss
- Configurable parameters in `core/config.py`

### Momentum
- Uses dual moving average crossover
- Trend-following with ATR-based position sizing
- Configurable parameters in `core/config.py`

### Scalping
- Uses RSI for entry signals
- Tighter stops and targets
- Volatility filtering with ATR
- Configurable parameters in `core/config.py`

## Usage

You can start a strategy directly from Python:

```python
from main import run_strategy

# Run scalping strategy on forex pairs with FTMO
run_strategy('scalping', 'FTMO', 'forex')

# Run momentum strategy on indices with Oanda
run_strategy('momentum', 'Oanda', 'indices')

# Run mean reversion on crypto with Exness
run_strategy('mean_reversion', 'Exness', 'crypto')
```

To stop a running strategy, use Ctrl+C in the terminal.

## Adding New Strategies

1. Create a new strategy class in `core/strategies/`
2. Inherit from `BaseTrader`
3. Implement `define_strategy()` and `execute_trades()`
4. Add configuration to `STRATEGY_CONFIGS` in `core/config.py`

## Risk Management

Each strategy includes:
- Position sizing based on account risk percentage
- ATR-based stop losses
- Risk:reward ratio management
- Maximum position checks

## Logging

The system logs:
- Trade execution
- Position updates
- Error handling
- Strategy signals

Logs are formatted with timestamp, level, and message.

## Directory Structure

```
quant-atc-mushini/
├── core/
│   ├── base_trader.py     # Base trading functionality
│   ├── config.py          # Configuration settings
│   ├── utils.py           # Technical indicators and helpers
│   └── strategies/        # Strategy implementations
│       ├── mean_reversion.py
│       ├── momentum.py
│       └── scalping.py
├── main.py                # Main execution script
└── requirements.txt       # Dependencies

