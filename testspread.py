import numpy as np

class MarketMaker:
    def __init__(self, alpha, sigma, S_eq, S_initial):
        self.alpha = alpha
        self.sigma = sigma
        self.S_eq = S_eq
        self.S = S_initial

    def calculate_spread_next(self, delta_t=1):
        # Calculate the next spread using the discrete time model
        noise = np.random.normal(0, 1)  # Draw from a standard normal distribution
        spread_next = self.S + delta_t * (-self.alpha * (self.S - self.S_eq)) + self.sigma * np.sqrt(delta_t) * noise
        return spread_next

    def calculate_rate_of_change(self, delta_t=1):
        # Calculate the next spread
        spread_next = self.calculate_spread_next(delta_t)
        # Calculate the rate of change per minute
        rate_of_change = (spread_next - self.S) / delta_t
        # Update the current spread for the next iteration
        self.S = spread_next
        return rate_of_change

    def simulate_to_minimum_ticksize(self, minimum_ticksize=2.5, max_minutes=60):
        rates_of_change = []
        for minute in range(max_minutes):
            rate = self.calculate_rate_of_change()
            rates_of_change.append(rate)
            print(f"Minute {minute + 1}: Spread = {self.S:.2f}, Rate of Change = {rate:.4f}")
            if self.S <= minimum_ticksize:
                print("Minimum tick size reached.")
                break
        return rates_of_change

# Example Usage
alpha = 0.1  # Mean reversion rate
sigma = 43  # Volatility
S_eq = 5.0   # Equilibrium spread
S_initial = 6.0  # Initial spread

market_maker = MarketMaker(alpha, sigma, S_eq, S_initial)
rates_of_change = market_maker.simulate_to_minimum_ticksize()
