import numpy as np
from tqdm import tqdm

#class vasof():
#Importing the OHLC data
#Using the function to add columns
def adder(Data, times):
    for i in range(1, times+1):
        z = np.nan * np.zeros((len(Data), 1), dtype = float)
        Data = np.append(Data, z, axis=1)
    return Data

#Function to delete certain number of columns
def deleter(Data, index, times):
    for i in range(1, times+1):
        Data = np.delete(Data, index, axis=1)
    return Data

#Function to slice a certain number of rows
def jump(Data, jump):
    Data = Data[jump:,]
    return Data

#Function to calculate volatility
def volatility(Data, lookback, what, where):
    for i in range(len(Data)):
        try:
            Data[i, where] = (Data[i-lookback + 1 : i + 1, what].std())
        except IndexError and ZeroDivisionError:
            pass
    return Data     

#Function to normalize standard deviation using Min/Max normalization method
def normalizer(Data, lookback, what, where):
    for i in range(len(Data)):
        try:
            Data[i, where] = (Data[i, what] - min(Data[i-lookback+1:i+1, what])) / (max(Data[i-lookback+1:i+1, what]) -
                                                                                    min(Data[i-lookback+1:i+1, what]))
        except ValueError:
            pass
    Data[:, where] = Data[:, where] * 100
    return Data  

#function to calculate the volatility adjusted stochastic oscillator based on fibonacci lookback periods
def fib_stoch(Data, volatility_lookback, what, where):
    Data = volatility(Data, volatility_lookback, what, where)
    Data = normalizer(Data, volatility_lookback, where, where+1)

    for i in range(len(Data)):
        Data[i, where+1] = round(Data[i, where+1], 0)

    for i in range(len(Data)):
        if Data[i, where+1] >= 0 and Data[i, where+1] <= 10:
            Data[i, where+1] = 144
        if Data[i, where+1] > 10 and Data[i, where+1] <= 20:
            Data[i, where+1] = 89
        if Data[i, where+1] > 20 and Data[i, where+1] <= 30:
            Data[i, where+1] = 55
        if Data[i, where+1] > 30 and Data[i, where+1] <= 40:
            Data[i, where+1] = 34
        if Data[i, where+1] > 40 and Data[i, where+1] <= 50:
            Data[i, where+1] = 21
        if Data[i, where+1] > 50 and Data[i, where+1] <= 60:
            Data[i, where+1] = 13
        if Data[i, where+1] > 60 and Data[i, where+1] <= 70:
            Data[i, where+1] = 8
        if Data[i, where+1] > 70 and Data[i, where+1] <= 80:
            Data[i, where+1] = 5
        if Data[i, where+1] > 80 and Data[i, where+1] <= 90:
            Data[i, where+1] = 3
        if Data[i, where+1] > 90 and Data[i, where+1] <= 100:
            Data[i, where+1] = 2
    Data = jump(Data, volatility_lookback)

    for i in tqdm(range(len(Data))):
        try:
            lookback = int(Data[i, where+1])
            Data[i, where+2] = (Data[i, what] - min(Data[i-lookback+1:i+1, 3])) / (max(Data[i-lookback+1:i+1, 2]) -
                                                                                    min(Data[i-lookback+1:i+1, 3]))
            Data[i, where+2] = round(Data[i, where+2], 2)
        except ValueError:
            pass
    Data[:, where+2] = Data[:, where+2] * 100
    return Data