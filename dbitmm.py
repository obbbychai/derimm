import asyncio
from dbitmm.dbitws import DbitWS
from dbitorders import Orders
from event_bus import EventBus

class DBMM:
    def __init__(self, dbit_ws, orders, event_bus):
        self.ws = dbit_ws
        self.orders = orders
        self.event_bus = event_bus
        self.positions = {}  # Track positions for each instrument

        # Subscribe to market data events
        self.event_bus.subscribe("market_data", self.on_market_data)

    async def on_market_data(self, event):
        instrument_name = event["instrument_name"]
        data = event["data"]

        # Calculate where to quote based on market data
        best_bid_price = data['best_bid_price']
        best_ask_price = data['best_ask_price']

        # Example logic to determine quote prices
        bid_quote = best_bid_price + 0.5  # Adjust as needed
        ask_quote = best_ask_price - 0.5  # Adjust as needed

        # Place orders
        await self.place_order(instrument_name, "buy", bid_quote)
        await self.place_order(instrument_name, "sell", ask_quote)

    async def place_order(self, instrument_name, direction, price):
        amount = 1  # Example amount, adjust as needed
        order_type = "limit"
        time_in_force = "good_til_cancelled"

        if direction == "buy":
            response = await self.orders.place_order(
                instrument_name=instrument_name,
                amount=amount,
                order_type=order_type,
                price=price,
                time_in_force=time_in_force
            )
        elif direction == "sell":
            response = await self.orders.place_order(
                instrument_name=instrument_name,
                amount=amount,
                order_type=order_type,
                price=price,
                time_in_force=time_in_force
            )

        # Update positions
        if response['result']['order_state'] == 'filled':
            if direction == "buy":
                self.positions[instrument_name] = self.positions.get(instrument_name, 0) + amount
            elif direction == "sell":
                self.positions[instrument_name] = self.positions.get(instrument_name, 0) - amount

        # Adjust quotes to maintain delta neutrality
        await self.adjust_quotes(instrument_name)

    async def adjust_quotes(self, instrument_name):
        # Example logic to adjust quotes to maintain delta neutrality
        position = self.positions.get(instrument_name, 0)
        if position > 0:
            # If long, place a sell order to reduce position
            best_ask_price = self.ws.order_book[instrument_name]["asks"]["price"].min()
            ask_quote = best_ask_price - 0.5  # Adjust as needed
            await self.place_order(instrument_name, "sell", ask_quote)
        elif position < 0:
            # If short, place a buy order to reduce position
            best_bid_price = self.ws.order_book[instrument_name]["bids"]["price"].max()
            bid_quote = best_bid_price + 0.5  # Adjust as needed
            await self.place_order(instrument_name, "buy", bid_quote)

# Example usage
async def main():
    # Create an instance of EventBus
    event_bus = EventBus()

    # Create an instance of DbitWS with the event bus
    dbit_ws = DbitWS(event_bus)
    await dbit_ws.connect()

    # Create an instance of Orders with the WebSocket connection and event bus
    orders = Orders(dbit_ws, event_bus)

    # Create an instance of DBMM
    market_maker = DBMM(dbit_ws, orders, event_bus)

    # Define the channels to subscribe to
    channels = ["quote.BTC-9AUG24", "quote.BTC-16AUG24"]

    # Subscribe to the desired channels
    await dbit_ws.subscribe(channels)

if __name__ == "__main__":
    asyncio.run(main())