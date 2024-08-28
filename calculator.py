# calculator.py
import math

class Calculator:
    def __init__(self, instrument_details):
        self.instrument_details = instrument_details

    def front_book(self, order_book_df):
        # Ensure the DataFrame is not empty
        if order_book_df is None or order_book_df.is_empty():
            return None

        # Calculate the best bid and ask prices
        best_bid = order_book_df.filter(order_book_df['side'] == 'bid')['price'].max()
        best_ask = order_book_df.filter(order_book_df['side'] == 'ask')['price'].min()

        # Calculate spread
        spread = best_ask - best_bid

        # Calculate mid price
        mid_price = (best_bid + best_ask) / 2 if best_bid and best_ask else None

        # Calculate weighted mid price
        weighted_mid_price = (
            (order_book_df[order_book_df['side'] == 'bid']['price'] * order_book_df[order_book_df['side'] == 'bid']['amount']).sum() +
            (order_book_df[order_book_df['side'] == 'ask']['price'] * order_book_df[order_book_df['side'] == 'ask']['amount']).sum()
        ) / (order_book_df['amount'].sum() if order_book_df['amount'].sum() > 0 else 1)

        # Calculate imbalance
        total_bid_amount = order_book_df[order_book_df['side'] == 'bid']['amount'].sum()
        total_ask_amount = order_book_df[order_book_df['side'] == 'ask']['amount'].sum()
        imbalance = (total_bid_amount - total_ask_amount) / (total_bid_amount + total_ask_amount) if (total_bid_amount + total_ask_amount) > 0 else 0

        return {
            "spread": spread,
            "mid_price": mid_price,
            "weighted_mid_price": weighted_mid_price,
            "imbalance": imbalance
        }

    def calculate_average_volatility(historical_volatility):
        if historical_volatility and isinstance(historical_volatility, list):
            # Extract the values from the result
            values = [item[1] for item in historical_volatility]  # item[1] is the volatility value
            average_volatility = sum(values) / len(values) if values else 0  # Calculate average
            return average_volatility
        return None





    def mid_price(bid_price, ask_price):
        """Calculate the mid price."""
        return (bid_price + ask_price) / 2

    def weighted_mid_price(bid_price, ask_price, bid_volume, ask_volume):
        """Calculate the weighted mid price."""
        return (bid_price * bid_volume + ask_price * ask_volume) / (bid_volume + ask_volume)

    def spread(bid_price, ask_price):
        """Calculate the spread."""
        return ask_price - bid_price

    def reservation_price(mid_price, inventory, gamma, volatility):
        """Calculate the reservation price."""
        return mid_price - inventory * gamma * (volatility ** 2)

    def optimal_spread(gamma, volatility, kappa):
        """Calculate the optimal spread."""
        return gamma * (volatility ** 2) + (2 / kappa) * math.log(1 + (kappa / (gamma * (volatility ** 2))))

    def bid_ask_quotes(reservation_price, optimal_spread):
        """Calculate the bid and ask quotes."""
        bid_quote = reservation_price - (optimal_spread / 2)
        ask_quote = reservation_price + (optimal_spread / 2)
        return bid_quote, ask_quote

    def update_quotes(bid_price, ask_price, bid_volume, ask_volume, inventory, gamma, volatility, kappa):
        """Calculate and update the bid and ask quotes based on Stoikov's model."""
        mid = mid_price(bid_price, ask_price)
        w_mid = weighted_mid_price(bid_price, ask_price, bid_volume, ask_volume)
        sprd = spread(bid_price, ask_price)
        res_price = reservation_price(mid, inventory, gamma, volatility)
        opt_spread = optimal_spread(gamma, volatility, kappa)
        bid_quote, ask_quote = bid_ask_quotes(res_price, opt_spread)
        
        return {
            'mid_price': mid,
            'weighted_mid_price': w_mid,
            'spread': sprd,
            'reservation_price': res_price,
            'optimal_spread': opt_spread,
            'bid_quote': bid_quote,
            'ask_quote': ask_quote
        }
