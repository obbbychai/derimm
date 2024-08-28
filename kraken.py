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
        self.order_book = {pair: {"bids": pl.DataFrame(columns=["price", "qty"]), "asks": pl.DataFrame(columns=["price", "qty"])} for pair in pairs}

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
                price = Decimal(price)
                qty = Decimal(qty)
                if qty == 0:
                    self.order_book[symbol]["bids"] = self.order_book[symbol]["bids"].filter(pl.col("price") != price)
                else:
                    self.order_book[symbol]["bids"] = pl.concat([self.order_book[symbol]["bids"], pl.DataFrame({"price": [price], "qty": [qty]})])

        # Update asks
        for ask in asks:
            price = ask.get("price")
            qty = ask.get("qty")
            if self.is_valid_decimal(price) and self.is_valid_decimal(qty):
                price = Decimal(price)
                qty = Decimal(qty)
                if qty == 0:
                    self.order_book[symbol]["asks"] = self.order_book[symbol]["asks"].filter(pl.col("price") != price)
                else:
                    self.order_book[symbol]["asks"] = pl.concat([self.order_book[symbol]["asks"], pl.DataFrame({"price": [price], "qty": [qty]})])

        # Truncate to the subscribed depth
        self.order_book[symbol]["bids"] = self.order_book[symbol]["bids"].sort("price", reverse=True).head(self.depth)
        self.order_book[symbol]["asks"] = self.order_book[symbol]["asks"].sort("price").head(self.depth)

        # Optionally, you can call a method to process the order book further
        self.process_order_book(symbol)

    def process_order_book(self, symbol):
        # Implement your logic here to do something with the order book
        # For example, analyze the order book, place trades, etc.
        print(f"Order Book for {symbol}:")
        print("Bids:")
        print(self.order_book[symbol]["bids"])
        print("Asks:")
        print(self.order_book[symbol]["asks"])

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