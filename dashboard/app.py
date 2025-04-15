from flask import Flask, render_template, request, redirect, url_for
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import start_strategy_process, stop_strategy_process, get_strategy_status
from core.config import BROKER_CONFIGS, SYMBOL_CONFIGS

app = Flask(__name__)

STRATEGIES = [
    'mean_reversion',
    'momentum',
    'scalping'
]

# Default broker and symbol type for demo; can be made dynamic
DEFAULT_BROKER = 'FTMO'
DEFAULT_SYMBOL_TYPE = 'forex'

@app.route('/')
def index():
    statuses = {s: get_strategy_status(s) for s in STRATEGIES}
    brokers = list(BROKER_CONFIGS.keys())
    symbol_types = list(SYMBOL_CONFIGS.keys())
    return render_template('index.html', strategies=STRATEGIES, statuses=statuses, brokers=brokers, symbol_types=symbol_types)

@app.route('/start/<strategy>', methods=['POST'])
def start_strategy(strategy):
    broker = request.form.get('broker')
    symbol_type = request.form.get('symbol_type')
    start_strategy_process(strategy, broker, symbol_type)
    return redirect(url_for('index'))

@app.route('/stop/<strategy>')
def stop_strategy(strategy):
    stop_strategy_process(strategy)
    return redirect(url_for('index'))

@app.route('/log/<strategy>')
def view_log(strategy):
    log_path = f'../logs/{strategy}.log'
    try:
        with open(log_path, 'r') as f:
            log_content = f.read()
    except Exception:
        log_content = 'No log available.'
    return render_template('log.html', strategy=strategy, log_content=log_content)

if __name__ == '__main__':
    app.run(debug=True)
