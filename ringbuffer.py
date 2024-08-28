import numpy as np  # Import NumPy for numerical calculations

class volBuffer:
    def __init__(self, size):
        self.size = size
        self.buffer = [0.0] * size  # Initialize the buffer with zeros
        self.index = 0  # Current index for the next write
        self.count = 0  # Count of elements added

    def add(self, value):
        self.buffer[self.index] = value  # Add the new value
        self.index = (self.index + 1) % self.size  # Move to the next index
        if self.count < self.size:
            self.count += 1  # Increase count until the buffer is full

    def average(self):
        return sum(self.buffer) / self.count if self.count > 0 else 0.0  # Calculate average

    def standard_deviation(self):
        if self.count < 3:
            print("not enough data to calculate std")
            return 0.0  # Not enough data to calculate standard deviation
        return np.std(self.buffer[:self.count])  # Calculate std deviation for filled part of the buffer

    def bollinger_bands(self, period=20, num_std_dev=3):
        if self.count < period:
            return None, None, None  # Not enough data to calculate Bollinger Bands
        mean = self.average()
        std_dev = self.standard_deviation()
        upper_band = mean + (num_std_dev * std_dev)
        lower_band = mean - (num_std_dev * std_dev)
        return mean, upper_band, lower_band