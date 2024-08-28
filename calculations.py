import math

def round_to_tick(price, tick_size=2.5):
    """Rounds the price to the nearest tick size."""
    return round(price / tick_size) * tick_size

def calculate_stoikov(order_book, inventory, current_volatility, risk_aversion, time_horizon, tick_size=2.5):
    # Ensure the order book is not empty
    if not order_book:
        raise ValueError("Order book is empty")

    # Retrieve the best bid and best ask
    best_bid = None
    best_ask = None

    # Iterate through the order book to find the best bid and ask
    for price, (side, amount) in order_book.items():
        if side == 'bid':
            if best_bid is None or price > best_bid:
                best_bid = price
        elif side == 'ask':
            if best_ask is None or price < best_ask:
                best_ask = price

    # Calculate mid price and spread
    if best_bid is not None and best_ask is not None:
        mid_price = (best_bid + best_ask) / 2
        spread = best_ask - best_bid
    else:
        print("Insufficient data to calculate mid price and spread.")
        return None, None, None, None, None, None

    # Calculate trade imbalance
    buy_volume = sum(amount for _, (side, amount) in order_book.items() if side == 'bid')
    sell_volume = sum(amount for _, (side, amount) in order_book.items() if side == 'ask')
    trade_imbalance = (buy_volume - sell_volume) / (buy_volume + sell_volume) if (buy_volume + sell_volume) > 0 else 0

    # Calculate optimal bid and ask using Stoikov model
    gamma = risk_aversion
    sigma = current_volatility
    T = time_horizon
    q = inventory

    reservation_price = mid_price - (q * gamma * sigma**2 * T)
    optimal_spread = gamma * sigma**2 * T + (2/gamma) * math.log(1 + (gamma/2))

    optimal_bid = reservation_price - optimal_spread / 2
    optimal_ask = reservation_price + optimal_spread / 2

    # Adjust optimal bid and ask based on trade imbalance
    imbalance_factor = 0.1  # Adjust this factor based on desired sensitivity
    optimal_bid += imbalance_factor * trade_imbalance * spread
    optimal_ask += imbalance_factor * trade_imbalance * spread

    # Round all calculated values to the nearest tick size
    mid_price = round_to_tick(mid_price, tick_size)
    spread = round_to_tick(spread, tick_size)
    best_bid = round_to_tick(best_bid, tick_size)
    best_ask = round_to_tick(best_ask, tick_size)
    optimal_bid = round_to_tick(optimal_bid, tick_size)
    optimal_ask = round_to_tick(optimal_ask, tick_size)

    return mid_price, spread, best_bid, best_ask, optimal_bid, optimal_ask