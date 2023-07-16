import numpy as np

class Vasof:
    def __init__(self, data):
        self.data = np.array(data.reset_index())
    
    def adder(self, times):
        for i in range(1, times+1):
            z = np.nan * np.zeros((len(self.data), 1), dtype=float)
            self.data = np.append(self.data, z, axis=1)
        return self.data

    def deleter(self, index, times):
        for i in range(1, times+1):
            self.data = np.delete(self.data, index, axis=1)
        return self.data

    def jump(self, jump):
        self.data = self.data[jump:,]
        return self.data

    def volatility(self, lookback, what, where):
        for i in range(len(self.data)):
            try:
                self.data[i, where] = (self.data[i-lookback + 1 : i + 1, what].std())
            except (IndexError, ZeroDivisionError):
                pass
        return self.data     

    def normalizer(self, lookback, what, where):
        for i in range(len(self.data)):
            try:
                self.data[i, where] = (self.data[i, what] - min(self.data[i-lookback+1:i+1, what])) / (max(self.data[i-lookback+1:i+1, what]) - min(self.data[i-lookback+1:i+1, what]))
            except ValueError:
                pass
        self.data[:, where] = self.data[:, where] * 100
        return self.data  

    def fib_stoch(self, volatility_lookback, what, where):
        self.data = self.volatility(volatility_lookback, what, where)
        self.data = self.normalizer(volatility_lookback, where, where+1)

        for i in range(len(self.data)):
            self.data[i, where+1] = round(self.data[i, where+1], 0)

        for i in range(len(self.data)):
            if self.data[i, where+1] >= 0 and self.data[i, where+1] <= 10:
                self.data[i, where+1] = 144
            if self.data[i, where+1] > 10 and self.data[i, where+1] <= 20:
                self.data[i, where+1] = 89
            if self.data[i, where+1] > 20 and self.data[i, where+1] <= 30:
                self.data[i, where+1] = 55
            if self.data[i, where+1] > 30 and self.data[i, where+1] <= 40:
                self.data[i, where+1] = 34
            if self.data[i, where+1] > 40 and self.data[i, where+1] <= 50:
                self.data[i, where+1] = 21
            if self.data[i, where+1] > 50 and self.data[i, where+1] <= 60:
                self.data[i, where+1] = 13
            if self.data[i, where+1] > 60 and self.data[i, where+1] <= 70:
                self.data[i, where+1] = 8
            if self.data[i, where+1] > 70 and self.data[i, where+1] <= 80:
                self.data[i, where+1] = 5
            if self.data[i, where+1] > 80 and self.data[i, where+1] <= 90:
                self.data[i, where+1] = 3
            if self.data[i, where+1] > 90 and self.data[i, where+1] <= 100:
                self.data[i, where+1] = 2
        self.data = self.jump(volatility_lookback)

        for i in range(len(self.data)):
            try:
                lookback = int(self.data[i, where+1])
                min_low = min(self.data[i-lookback+1:i+1, 3])
                max_high = max(self.data[i-lookback+1:i+1, 2])
                if max_high != min_low:
                    self.data[i, where+2] = (self.data[i, what] - min_low) / (max_high - min_low)
                self.data[i, where+2] = round(self.data[i, where+2], 2)
            except ValueError:
                pass
        self.data[:, where+2] = self.data[:, where+2] * 100
        return self.data
