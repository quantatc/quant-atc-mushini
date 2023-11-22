@echo off
cd "C:\Users\anstochibamu\anaconda3"

start cmd /k "call scripts\activate.bat && python C:\Users\anstochibamu\Documents\GitHub\quant-atc-mushini\mystery_of_the_missing_heart-algos\moth_scalping101_xm.py"
timeout /t 2
start cmd /k "call scripts\activate.bat && python C:\Users\anstochibamu\Documents\GitHub\quant-atc-mushini\mystery_of_the_missing_heart-algos\moth_volatility_deriv.py"
timeout /t 2
start cmd /k "call scripts\activate.bat && python C:\Users\anstochibamu\Documents\GitHub\quant-atc-mushini\mystery_of_the_missing_heart-algos\moth_scalping101_oanda.py"
timeout /t 2
start cmd /k "call scripts\activate.bat && python C:\Users\anstochibamu\Documents\GitHub\quant-atc-mushini\mystery_of_the_missing_heart-algos\moth_scalping101_binance.py"
