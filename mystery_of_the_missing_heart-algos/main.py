import threading
import time
from dotenv import load_dotenv
import os

def run_script(script_name, env_path):
    load_dotenv(dotenv_path=env_path)
    os.system(f"python {script_name}")

env_path = r"C:\Users\anstochibamu\Documents\GitHub\quant-atc-mushini\mystery_of_the_missing_heart-algos\.env"
directory = r"C:\Users\anstochibamu\Documents\GitHub\quant-atc-mushini\mystery_of_the_missing_heart-algos"

# Create threads for each script
# thread1 = threading.Thread(target=run_script, args=(directory + r"\moth_scalping101_xm.py", env_path))
thread1 = threading.Thread(target=run_script, args=(directory + r"\moth_scalping101_oanda.py", env_path))
thread2 = threading.Thread(target=run_script, args=(directory + r"\moth_volatility_deriv.py", env_path))
thread3 = threading.Thread(target=run_script, args=(directory + r"\moth_scalping101_binance.py", env_path))

# Start threads
thread1.start()
time.sleep(3)  # Delay to prevent clashes
thread2.start()

time.sleep(3)
thread3.start()

# time.sleep(3)  # Delay to prevent clashes
# thread4.start()

# Join threads
thread1.join()
thread2.join()
thread3.join()
# thread4.join()