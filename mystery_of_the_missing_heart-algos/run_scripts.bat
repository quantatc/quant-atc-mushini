@echo off
cd "C:\Users\ansto\anaconda3"

start cmd /k "call scripts\activate.bat && python C:\Users\ansto\Documents\anstolytics-research\quant-atc-mushini\quant-atc-mushini\mystery_of_the_missing_heart_XM2\moth_nas100.py"
timeout /t 2
start cmd /k "call scripts\activate.bat && python C:\Users\ansto\Documents\anstolytics-research\quant-atc-mushini\quant-atc-mushini\mystery_of_the_missing_heart_Oanda\moth_scalping101.py"
timeout /t 2
start cmd /k "call scripts\activate.bat && python C:\Users\ansto\Documents\anstolytics-research\quant-atc-mushini\quant-atc-mushini\mystery_of_the_missing_heart_Deriv\moth_volatility.py"
timeout /t 2
start cmd /k "call scripts\activate.bat && python C:\Users\ansto\Documents\anstolytics-research\quant-atc-mushini\quant-atc-mushini\crypto_scalping101_moth\moth-scalping101.py"
