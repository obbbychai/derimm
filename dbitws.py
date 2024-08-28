import asyncio
import websockets
import orjson
import hmac
import hashlib
import time
import config
from ringbuffer import volBuffer
from bintrees import RBTree
from calculations import calculate_stoikov
from oms import PendingOrderTracker, Order
import numpy as np
from collections import defaultdict





class DbitWS:
    def __init__(self):
        self.client_id = config.CLIENT_ID
        self.client_secret = config.CLIENT_SECRET
        self.url = config.DERIBIT_URL
        self.websocket = None
        self.access_token = None
        self.refresh_token = None
        self.order_book = RBTree()  # DataFrame to hold order book data
        self.trades_df = None  # DataFrame to hold trade data
        self.current_volatility = None
        self.volatility_buffer = volBuffer(size=30)
        self.inventory = 0
        self.instrument_details = {}
        self.order_tracker = PendingOrderTracker()
        self.last_change_id = None  # Track the last change ID
        self.order_states = defaultdict(dict)
        self.message_queue = asyncio.Queue()  # Create a queue for incoming messages
        self.listening = False

    async def connect(self):
        self.websocket = await websockets.connect(self.url)
        await self.authenticate()

    async def authenticate(self):
        timestamp, nonce, signature = self.generate_signature()
        auth_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "public/auth",
            "params": {
                "grant_type": "client_signature",
                "client_id": self.client_id,
                "timestamp": timestamp,
                "signature": signature,
                "nonce": nonce
            }
        }
        await self.send_message(auth_message)
        response = await self.receive_message()

        if 'result' in response and 'access_token' in response['result']:
            self.access_token = response['result']['access_token']
            self.refresh_token = response['result']['refresh_token']
            print("Authentication successful, access and refresh tokens saved.")
        else:
            print("Authentication failed:", response)

    async def subscribe_channels(self, public_channels, private_channels):
        # Subscribe to public channels
        if public_channels:
            public_msg = {
                "jsonrpc": "2.0",
                "method": "public/subscribe",
                "id": 42,
                "params": {
                    "channels": public_channels
                }
            }
            await self.send_message(public_msg)
            print(f"Subscribed to public channels: {public_channels}")

        # Subscribe to private channels
        if private_channels:
            if not self.access_token:
                print("Access token not available. Please authenticate first.")
                return

            private_msg = {
                "jsonrpc": "2.0",
                "method": "private/subscribe",
                "id": 43,
                "params": {
                    "access_token": self.access_token,
                    "channels": private_channels
                }
            }
            await self.send_message(private_msg)
            print(f"Subscribed to private channels: {private_channels}")

        # Start listening for incoming messages in a separate task
        asyncio.create_task(self.listen_for_messages())

    async def listen_for_messages(self):
        while True:
            try:
                response = await self.websocket.recv()
                response = orjson.loads(response)
                await self.message_queue.put(response)  # Put the response in the queue
            except websockets.exceptions.ConnectionClosed:
                print("WebSocket connection closed. Reconnecting...")
                await self.connect()

    async def send_message(self, message):
        def convert_numpy(obj):
            if isinstance(obj, np.float64):
                return float(obj)
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        serialized_message = orjson.dumps(message, default=convert_numpy).decode('utf-8')
        await self.websocket.send(serialized_message)

    async def receive_message(self):
        return await self.message_queue.get()
    
    
    def generate_signature(self):
        timestamp = int(time.time() * 1000)
        nonce = "nonce"
        data = ""
        message = f"{timestamp}\n{nonce}\n{data}"
        signature = hmac.new(self.client_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
        return timestamp, nonce, signature


    async def process_message(self, message):
        if 'id' in message:
            if message['id'] == 888:  # Handle buy order result specifically
                await self.handle_order_result(message)
                return  # Exit early to avoid further processing

            if message['id'] == 555:  # Handle sell order result
                await self.handle_order_result(message)
                return 

        if 'params' in message and 'data' in message['params']:
            channel = message['params']['channel']
            if channel.startswith("book."):
                await self.process_order_book_message(message)
            elif channel.startswith("user.orders"):
                await self.process_user_orders(message)  # Add this line
            elif channel.startswith("user.changes"):
                await self.process_user_changes(message)
            elif channel.startswith("chart.trades"):
                await self.process_chart_trades_message(message)
            elif channel.startswith("deribit_volatility_index"):
                await self.process_volatility_index_message(message)
            elif channel == "user.portfolio.btc":  # Handle portfolio data
                await self.process_user_portfolio(message)
        else:
            print("Received message without 'method':", message)  # Log unexpected messages

    async def process_user_orders(self, message):
        if 'params' in message and 'data' in message['params']:
            data = message['params']['data']
            order_id = data['order_id']
            instrument_name = data['instrument_name']
            self.order_states[instrument_name][order_id] = data
            print(f"Updated order state: {data}")


    async def get_order_state(self, instrument_name, order_id):
        # Check if we have the order state cached
        if order_id in self.order_states[instrument_name]:
            return self.order_states[instrument_name][order_id]
        else:
            print(f"Order state not found for order ID: {order_id}")
            return None



    async def process_user_orders(self, message):
        if 'params' in message and 'data' in message['params']:
            data = message['params']['data']
            order_id = data['order_id']
            instrument_name = data['instrument_name']
            self.order_states[instrument_name][order_id] = data
            print(f"Updated order state: {data}")



    async def process_user_portfolio(self, message):
        print("Processing user portfolio message:", message)
        if 'params' in message and 'data' in message['params']:
            data = message['params']['data']

            # Extract relevant fields from the portfolio data
            self.portfolio_data = {
                "maintenance_margin": data.get("maintenance_margin"),
                "delta_total": data.get("delta_total"),
                "session_upl": data.get("session_upl"),
                "balance": data.get("balance"),
                "available_funds": data.get("available_funds"),  # Store available funds
                "total_pl": data.get("total_pl"),
                "equity": data.get("equity"),
                "available_withdrawal_funds": data.get("available_withdrawal_funds"),
                # Add any other fields you need
            }

            # Store available funds for market making
            self.inventory = self.portfolio_data["available_funds"]

            print("Updated Portfolio Data:")
            print(self.portfolio_data)

            return self.portfolio_data  # Return the portfolio data
        return None  # Return None if the data is not available

    async def process_volatility_index_message(self, message):
        #print("Processing volatility index message:", message)
        if 'params' in message and 'data' in message['params']:
            data = message['params']['data']
            self.current_volatility = data.get('volatility')
            volatility = data.get('volatility')
            timestamp = data.get('timestamp')
            index_name = data.get('index_name')

            # Add the new volatility value to the ring buffer
            self.volatility_buffer.add(volatility)

            # Print the current average volatility
            avg_volatility = self.volatility_buffer.average()
            #print(f"Current Average Volatility: {avg_volatility}")

            # Calculate Bollinger Bands
            mean, upper_band, lower_band = self.volatility_buffer.bollinger_bands(period=20, num_std_dev=2)
            if mean is not None:
                None
            else:
                print(f"waiting for buffer to fill to calclulate mean and bands. Current vol: {volatility}")


    async def get_historical_volatility(self, currency):
        msg = {
            "jsonrpc": "2.0",
            "id": 8387,  # Unique ID for the request
            "method": "public/get_historical_volatility",
            "params": {
                "currency": currency
            }
        }

        await self.send_message(msg)  # Send the request message
        response = await self.receive_message()  # Wait for the response

        # Debugging output
        print("Response from get_historical_volatility:", response)

        # Check if the response contains the result
        if 'result' in response:
            historical_volatility = response['result']  # Get the result array
            return historical_volatility  # Return the list of lists directly
        else:
            print("Error retrieving historical volatility:", response)
            return None  # Return None or handle the error as needed


    async def process_chart_trades_message(self, message):
        print("Processing chart trades message:", message)
        if 'params' in message and 'data' in message['params']:
            data = message['params']['data']
            volume = data.get('volume')
            tick = data.get('tick')
            open_price = data.get('open')
            low_price = data.get('low')
            high_price = data.get('high')
            cost = data.get('cost')
            close_price = data.get('close')

            # Create a new trade dictionary
            new_trade = {
                "tick": tick,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
                "cost": cost
            }

            # Add the new trade to the ring buffer
            self.chart_trade_buffer.add(new_trade)

            print("Updated Chart Trades Ring Buffer:")
            print(self.chart_trade_buffer.get_all())  # Print all trades in the buffer

            # Return the processed trade data for further calculations
            return new_trade

    async def process_user_changes(self, message):
        if 'params' in message and 'data' in message['params']:
            data = message['params']['data']
            channel = message['params']['channel']

            # Extract trades, positions, and orders
            trades = data.get('trades', [])
            positions = data.get('positions', [])
            orders = data.get('orders', [])
            instrument_name = data.get('instrument_name')

            # Process trades
            for trade in trades:
                print(f"Trade ID: {trade['trade_id']}, Price: {trade['price']}, Amount: {trade['amount']}, Direction: {trade['direction']}, instrument name: {trade['instrument_name']}")
                return {
                    "trade_id": trade['trade_id'],
                    "price": trade['price'],
                    "amount": trade['amount'],
                    "direction": trade['direction'],
                    "instrument_name": instrument_name
                }

            # Process positions
            for position in positions:
                print(f"Position for {instrument_name}: Size: {position['size']}, Total P&L: {position['total_profit_loss']}")
                return {
                    "size": position['size'],
                    "total_profit_loss": position['total_profit_loss'],
                    "instrument_name": instrument_name
                }

            # Process orders
            for order in orders:
                order_id = order['order_id']
                state = order['order_state']
                price = order['price']
                amount = order['amount']
                side = order['direction']  # Assuming 'direction' indicates 'buy' or 'sell'
                timestamp = order['creation_timestamp'] / 1000.0  # Convert to seconds

                # Create an Order object
                order_obj = Order(id=order_id, price=price, quantity=amount, side=side, timestamp=timestamp, status=state)

                # Update the order in the tracker
                if state in ['open', 'filled', 'cancelled']:  # Adjust based on your order states
                    self.order_tracker.add_order(order_obj)
                    print(f"Order added to tracker: {order_obj}")
                else:
                    # If the order is no longer valid, remove it from the tracker
                    self.order_tracker.remove_order(order_id)
                    print(f"Order removed from tracker: {order_id}")

                return {
                    "order_id": order_id,
                    "state": state,
                    "price": price,
                    "amount": amount,
                    "instrument_name": instrument_name
                }

    async def process_order_book_message(self, message):
        if 'params' in message and 'data' in message['params']:
            data = message['params']['data']
            channel = message['params']['channel']

            if channel.startswith("book."):
                if data['type'] == "snapshot":
                    # Initialize the RBTree with the full order book
                    bids = data['bids']
                    asks = data['asks']
                    self.order_book.clear()  # Clear existing order book

                    for bid in bids:
                        price, amount = bid[1], bid[2]
                        self.order_book.insert(price, ('bid', amount))  # Insert bids

                    for ask in asks:
                        price, amount = ask[1], ask[2]
                        self.order_book.insert(price, ('ask', amount))  # Insert asks

                    self.last_change_id = data['change_id']
                    #print("Order Book Snapshot:")
                    #print(self.order_book)  # Print the order book

                elif data['type'] == "change":
                    change_id = data['change_id']
                    prev_change_id = data.get('prev_change_id')

                    if prev_change_id == self.last_change_id:
                        # Process changes
                        for action, price, amount in data['bids']:
                            if action == "delete":
                                if price in self.order_book:
                                    del self.order_book[price]  # Remove bid
                            else:  # "new" or "change"
                                self.order_book.insert(price, ('bid', amount))  # Update or insert bid

                        for action, price, amount in data['asks']:
                            if action == "delete":
                                if price in self.order_book:
                                    del self.order_book[price]  # Remove ask
                            else:  # "new" or "change"
                                self.order_book.insert(price, ('ask', amount))  # Update or insert ask

                        self.last_change_id = change_id
                        #print(f"Updated Order Book: {self.order_book}") 
                        mid_price, spread, best_bid, best_ask, optimal_bid, optimal_ask = calculate_stoikov(
                            self.order_book, 
                            self.inventory,
                            self.current_volatility, 
                            self.risk_aversion,
                            self.time_horizon,  # Pass the time_horizon value from the DbitWS instance
                            tick_size=2.5
                        )
                        return self.order_book

    async def place_buy(self, instrument_name, amount, order_type, label, price=None, post_only=True):
        msg = {
            "jsonrpc": "2.0",
            "id": 888,  # You can generate a unique ID for each order
            "method": "private/buy",
            "params": {
                "instrument_name": instrument_name,
                "amount": amount,
                "type": order_type,
                "label": label
            }
        }
        
        if order_type == "limit" and price is not None:
            msg["params"]["price"] = price
            msg["params"]["post_only"] = post_only

        await self.send_message(msg)
        response = await self.receive_message()
        order_id = response.get('result', {}).get('order', {}).get('order_id')
        print(f"Order placed: {msg}, Order ID: {order_id}")
        return order_id


    async def place_sell(self, instrument_name, amount, order_type, label, price=None, post_only=True):
        msg = {
            "jsonrpc": "2.0",
            "id": 555,  # You can generate a unique ID for each order
            "method": "private/sell",
            "params": {
                "instrument_name": instrument_name,
                "amount": amount,
                "type": order_type,
                "label": label
            }
        }
    
        if order_type == "limit" and price is not None:
            msg["params"]["price"] = price
            msg["params"]["post_only"] = post_only

        await self.send_message(msg)
        response = await self.receive_message()
        order_id = response.get('result', {}).get('order', {}).get('order_id')
        print(f"Order placed: {msg}, Order ID: {order_id}")
        return order_id
        
    
    
    
    async def cancel_all_orders(self):
        msg = {
            "jsonrpc": "2.0",
            "id": 444,  # You can generate a unique ID for each order
            "method": "private/cancel_all",
            "params": {}
        }

        await self.send_message(msg)
        print(f"Cancelling all orders: {msg}")

        # Wait for the response
        response = await self.receive_message()
        print("Response from cancel all orders:", response)



    async def handle_order_result(self, message):
        order_data = message.get('result', {}).get('order', {})
        if order_data:
            # Extract relevant fields
            order_id = order_data.get('order_id')
            price = order_data.get('price')
            quantity = order_data.get('amount')
            side = order_data.get('direction')  # Assuming 'direction' indicates 'buy' or 'sell'
            timestamp = order_data.get('creation_timestamp') / 1000.0  # Convert to seconds
            status = order_data.get('order_state')
            instrument_name = order_data.get('instrument_name')
            label = order_data.get('label')

            # Create an Order object
            order = Order(id=order_id, price=price, quantity=quantity, side=side, timestamp=timestamp, instrument_name=instrument_name, status=status)

            # Store additional order details
            order_details = {
                "order_id": order_id,
                "order_state": status,
                "amount": quantity,
                "instrument_name": instrument_name,
                "direction": side,
                "price": price,
                "label": label
            }

            # Track pending orders based on the message ID
            if message.get('id') == 888:  # Buy order
                self.order_tracker.add_order(order)  # Add to tracker for buy orders
                print(f"Pending Buy Order added: {order}, Details: {order_details}")
            elif message.get('id') == 555:  # Sell order
                self.order_tracker.add_order(order)  # Add to tracker for sell orders
                print(f"Pending Sell Order added: {order}, Details: {order_details}")
            else:
                print(f"Unknown order ID: {message.get('id')}. Cannot determine order type.")