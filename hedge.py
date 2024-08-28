class Hedged:
    def __init__(self, stablecoin_pair, trading_volume):
        self.stablecoin_pair = stablecoin_pair
        self.trading_volume = trading_volume
        self.kraken_fee_structure = self.get_fee_structure(trading_volume)

    def get_fee_structure(self, volume):
        """
        Determine the fee percentage based on the 30-day trading volume.
        
        :param volume: The 30-day trading volume in USD.
        :return: The fee percentage for the stablecoin pair.
        """
        if volume <= 50000:
            return 0.0020  # 0.20%
        elif volume <= 100000:
            return 0.0016  # 0.16%
        elif volume <= 250000:
            return 0.0012  # 0.12%
        elif volume <= 500000:
            return 0.0008  # 0.08%
        elif volume <= 1000000:
            return 0.0004  # 0.04%
        elif volume <= 10000000:
            return 0.0002  # 0.02%
        elif volume <= 100000000:
            return 0.0000  # 0.00% maker, 0.01% taker
        else:
            return 0.0000  # 0.00% maker, 0.001% taker

    def is_delta_neutral(self, long_position, short_position):
        """
        Check if the portfolio is delta neutral.
        
        :param long_position: The delta of the long position.
        :param short_position: The delta of the short position.
        :return: True if delta neutral, False otherwise.
        """
        return long_position + short_position == 0

    def required_quote_spread(self, market_price):
        """
        Calculate the required quote spread to be profitable market making.
        
        :param market_price: The current market price of the stablecoin pair.
        :return: The required spread to cover fees and be profitable.
        """
        # Calculate the required spread
        required_spread = market_price * self.kraken_fee_structure
        return required_spread

# Example usage
if __name__ == "__main__":
    # Example trading volume
    trading_volume = 75000  # Example 30-day trading volume in USD

    hedged = Hedged("USDC/USD", trading_volume)

    # Check if delta neutral
    long_position = 100  # Example long delta
    short_position = -100  # Example short delta
    print("Is delta neutral:", hedged.is_delta_neutral(long_position, short_position))

    # Calculate required quote spread
    market_price = 1.00  # Example market price
    spread = hedged.required_quote_spread(market_price)
    print("Required quote spread for profitability:", spread)