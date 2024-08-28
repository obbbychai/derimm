from dbitws import DbitWS
from event_bus import EventBus

class Orders:
    def __init__(self, dbit_ws, event_bus):
        self.ws = dbit_ws
        self.event_bus = event_bus

    async def place_order(self, instrument_name, amount=None, contracts=None, order_type="limit", price=None, time_in_force="good_til_cancelled", **kwargs):
        order_message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "private/buy" if order_type == "buy" else "private/sell",
            "params": {
                "instrument_name": instrument_name,
                "type": order_type,
                "time_in_force": time_in_force,
                "amount": amount,
                "price": price,
                **kwargs
            }
        }
        if contracts is not None:
            order_message["params"]["contracts"] = contracts

        await self.ws.send_message(order_message)
        response = await self.ws.message_queue.get()
        print("Order Response:", response)
        return response

# Example usage
async def main():
    # Create an instance of EventBus
    event_bus = EventBus()

    # Create an instance of DbitWS and connect
    dbit_ws = DbitWS(event_bus)
    await dbit_ws.connect()

    # Create an instance of Orders with the WebSocket connection
    orders = Orders(dbit_ws, event_bus)

    # Place a buy order
    response = await orders.place_order(
        instrument_name="BTC-16AUG24",
        amount=1,
        order_type="limit",
        price=60000,
        time_in_force="good_til_cancelled"
    )

if __name__ == "__main__":
    asyncio.run(main())