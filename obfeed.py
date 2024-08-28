import asyncio
import websockets
import ujson
from decimal import Decimal, InvalidOperation
import zlib  # For CRC32 checksum calculation
import polars as pl  # Import Polars

class OBFeed:
    def __init__(self, pairs, depth=10):
        self.url = "wss://ws.kraken.com/v2"
        self.pairs = pairs
        self.depth = depth
        # Initialize order book with empty DataFrames with explicit schema
        self.order_book = {
            pair: {
                "bids": pl.DataFrame({"price": pl.Series(dtype=pl.Utf8), "qty": pl.Series(dtype=pl.Utf8)}),
                "asks": pl.DataFrame({"price": pl.Series(dtype=pl.Utf8), "qty": pl.Series(dtype=pl.Utf8)}),
                "midprice": pl.Series(dtype=pl.Utf8),  # New column for midprice
                "weighted_midprice": pl.Series(dtype=pl.Utf8),  # New column for weighted midprice
                "imbalance": pl.Series(dtype=pl.Utf8)  # New column for imbalance
            } for pair in pairs
        }

    async def subscribe(self):
        async with websockets.connect(self.url) as websocket:
            subscribe_message = {
                "method": "subscribe",
                "params": {
                    "channel": "book",
                    "symbol": self.pairs,
                    "depth": self.depth,
                    "snapshot": True
                }
            }
            await websocket.send(ujson.dumps(subscribe_message))
            await self.listen(websocket)

    async def listen(self, websocket):
        while True:
            message = await websocket.recv()
            await self.process_message(message)

    async def process_message(self, message):
        print(f"Received message: {message}")  # Log the raw message
        data = ujson.loads(message)  # Only one argument

        if data.get("channel") == "book":
            if data.get("type") == "snapshot":
                self.update_order_book(data["data"][0])
            elif data.get("type") == "update":
                self.update_order_book(data["data"][0])
            self.checksum(data["data"][0])

    def is_valid_decimal(self, value):
        """Check if the value can be converted to Decimal."""
        try:
            Decimal(value)
            return True
        except (ValueError, InvalidOperation):
            return False

    def update_order_book(self, data):
        symbol = data["symbol"]
        bids = data.get("bids", [])
        asks = data.get("asks", [])

        # Update bids
        for bid in bids:
            price = bid.get("price")
            qty = bid.get("qty")
            if self.is_valid_decimal(price) and self.is_valid_decimal(qty):
                # Store as strings to avoid Decimal128 limitations
                if qty == 0:
                    self.order_book[symbol]["bids"] = self.order_book[symbol]["bids"].filter(pl.col("price") != str(price))
                else:
                    new_bid = pl.DataFrame({"price": [str(price)], "qty": [str(qty)]})
                    self.order_book[symbol]["bids"] = pl.concat([self.order_book[symbol]["bids"], new_bid])

        # Update asks
        for ask in asks:
            price = ask.get("price")
            qty = ask.get("qty")
            if self.is_valid_decimal(price) and self.is_valid_decimal(qty):
                # Store as strings to avoid Decimal128 limitations
                if qty == 0:
                    self.order_book[symbol]["asks"] = self.order_book[symbol]["asks"].filter(pl.col("price") != str(price))
                else:
                    new_ask = pl.DataFrame({"price": [str(price)], "qty": [str(qty)]})
                    self.order_book[symbol]["asks"] = pl.concat([self.order_book[symbol]["asks"], new_ask])

        # Calculate midprice, weighted midprice, imbalance, and micro-price
        self.calculate_midprice(symbol)
        self.calculate_weighted_midprice(symbol)
        self.calculate_imbalance(symbol)
        micro_price = self.calculate_micro_price(symbol)
        print(f"Micro-Price for {symbol}: {micro_price:.6f}" if micro_price is not None else "Micro-Price could not be calculated.")

        # Calculate standard deviation bounds
        upper_bound, lower_bound = self.calculate_std_bounds(symbol)
        if upper_bound is not None and lower_bound is not None:
            print(f"Upper Bound (1 Std Devs above): {upper_bound:.6f}")
            print(f"Lower Bound (1 Std Devs below): {lower_bound:.6f}")

        # Optionally, you can call a method to process the order book further
        self.process_order_book(symbol)

    def calculate_midprice(self, symbol):
        """
        Calculate the midprice based on the highest bid and lowest ask.
        """
        if not self.order_book[symbol]["bids"].is_empty() and not self.order_book[symbol]["asks"].is_empty():
            highest_bid = float(self.order_book[symbol]["bids"]["price"].to_numpy()[0])  # Highest bid price
            lowest_ask = float(self.order_book[symbol]["asks"]["price"].to_numpy()[0])  # Lowest ask price
            midprice = (highest_bid + lowest_ask) / 2
            self.order_book[symbol]["midprice"] = pl.Series([str(midprice)])  # Store midprice as string

    def calculate_weighted_midprice(self, symbol):
        """
        Calculate the weighted midprice based on the bids and asks.
        """
        if not self.order_book[symbol]["bids"].is_empty() and not self.order_book[symbol]["asks"].is_empty():
            bids = self.order_book[symbol]["bids"]
            asks = self.order_book[symbol]["asks"]

            # Calculate weighted sums
            total_bid_qty = bids["qty"].cast(pl.Float64).sum()
            total_ask_qty = asks["qty"].cast(pl.Float64).sum()

            weighted_bid_sum = (bids["price"].cast(pl.Float64) * bids["qty"].cast(pl.Float64)).sum()
            weighted_ask_sum = (asks["price"].cast(pl.Float64) * asks["qty"].cast(pl.Float64)).sum()

            # Calculate weighted midprice
            weighted_midprice = (weighted_bid_sum + weighted_ask_sum) / (total_bid_qty + total_ask_qty)
            self.order_book[symbol]["weighted_midprice"] = pl.Series([str(weighted_midprice)])  # Store as string

    def calculate_imbalance(self, symbol):
        """
        Calculate the imbalance based on the total quantities of bids and asks.
        """
        if not self.order_book[symbol]["bids"].is_empty() and not self.order_book[symbol]["asks"].is_empty():
            total_bid_qty = self.order_book[symbol]["bids"]["qty"].cast(pl.Float64).sum()
            total_ask_qty = self.order_book[symbol]["asks"]["qty"].cast(pl.Float64).sum()

            # Calculate imbalance
            imbalance = (total_bid_qty - total_ask_qty) / (total_bid_qty + total_ask_qty) if (total_bid_qty + total_ask_qty) != 0 else 0
            self.order_book[symbol]["imbalance"] = pl.Series([str(imbalance)])  # Store as string

    def process_order_book(self, symbol):
        """
        Process and display the order book for the given symbol.
        """
        print(f"Order Book for {symbol}:")
        
        # Display Bids
        print("Bids:")
        print(self.order_book[symbol]["bids"])

        # Display Asks
        print("Asks:")
        print(self.order_book[symbol]["asks"])

        # Display Midprice
        midprice = self.order_book[symbol]["midprice"].to_numpy()[0] if not self.order_book[symbol]["midprice"].is_empty() else "N/A"
        print(f"Midprice: {midprice}")

        # Display Weighted Midprice
        weighted_midprice = self.order_book[symbol]["weighted_midprice"].to_numpy()[0] if not self.order_book[symbol]["weighted_midprice"].is_empty() else "N/A"
        print(f"Weighted Midprice: {weighted_midprice}")

        # Display Imbalance
        imbalance = self.order_book[symbol]["imbalance"].to_numpy()[0] if not self.order_book[symbol]["imbalance"].is_empty() else "N/A"
        print(f"Imbalance: {imbalance}")

        print("\n" + "="*40 + "\n")  # Separator for clarity

    def calculate_micro_price(self, symbol):
        """
        Calculate the micro-price based on the current bids and asks.
        """
        if not self.order_book[symbol]["bids"].is_empty() and not self.order_book[symbol]["asks"].is_empty():
            bids = self.order_book[symbol]["bids"]
            asks = self.order_book[symbol]["asks"]

            # Calculate weighted sums for bids
            weighted_bid_sum = (bids["price"].cast(pl.Float64) * bids["qty"].cast(pl.Float64)).sum()
            total_bid_qty = bids["qty"].cast(pl.Float64).sum()

            # Calculate weighted sums for asks
            weighted_ask_sum = (asks["price"].cast(pl.Float64) * asks["qty"].cast(pl.Float64)).sum()
            total_ask_qty = asks["qty"].cast(pl.Float64).sum()

            # Calculate micro-price
            total_weighted_sum = weighted_bid_sum + weighted_ask_sum
            total_qty = total_bid_qty + total_ask_qty

            micro_price = total_weighted_sum / total_qty if total_qty != 0 else 0
            return micro_price
        return None  # Return None if there are no bids or asks
    
    def calculate_std_deviation(self, symbol):
        """
        Calculate the standard deviation of the prices in the order book.
        """
        if not self.order_book[symbol]["bids"].is_empty() and not self.order_book[symbol]["asks"].is_empty():
            # Combine bids and asks prices
            bids_prices = self.order_book[symbol]["bids"]["price"].cast(pl.Float64)
            asks_prices = self.order_book[symbol]["asks"]["price"].cast(pl.Float64)
            
            # Concatenate bids and asks prices
            all_prices = pl.concat([bids_prices, asks_prices])
            
            # Calculate standard deviation
            std_dev = all_prices.std()
            return std_dev
        return None  # Return None if there are no bids or asks

    def calculate_std_bounds(self, symbol):
        """
        Calculate the upper and lower bounds based on the micro-price and standard deviation.
        """
        micro_price = self.calculate_micro_price(symbol)
        std_dev = self.calculate_std_deviation(symbol)

        if micro_price is not None and std_dev is not None:
            upper_bound = micro_price + std_dev  # 1 Std Dev above
            lower_bound = micro_price - std_dev  # 1 Std Dev below
            return upper_bound, lower_bound
        return None, None  # Return None if micro-price or std_dev could not be calculated




    def checksum(self, data):
        # Calculate checksum for the top 10 bids and asks
        bids = data.get("bids", [])[:10]
        asks = data.get("asks", [])[:10]

        checksum_string = ""

        # Process asks
        for price, qty in asks:
            price_str = str(price).replace('.', '').lstrip('0')
            qty_str = str(qty).replace('.', '').lstrip('0')
            checksum_string += f"{price_str}{qty_str}"

        # Process bids
        for price, qty in bids:
            price_str = str(price).replace('.', '').lstrip('0')
            qty_str = str(qty).replace('.', '').lstrip('0')
            checksum_string += f"{price_str}{qty_str}"

        # Calculate CRC32 checksum
        checksum_value = zlib.crc32(checksum_string.encode()) & 0xffffffff
        print(f"Checksum: {checksum_value}")

# Example usage
async def main():
    # User input for pairs and depth
    pairs = input("Enter currency pairs (comma-separated, e.g., 'XBT/USD,ETH/USD'): ").split(',')
    depth = int(input("Enter depth (10, 25, 100, 500, 1000): "))

    # Validate depth
    if depth not in [10, 25, 100, 500, 1000]:
        print("Invalid depth. Defaulting to 10.")
        depth = 10

    ws_feed = OBFeed(pairs, depth)
    await ws_feed.subscribe()

if __name__ == "__main__":
    asyncio.run(main())