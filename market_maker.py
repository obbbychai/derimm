import asyncio
from dbitmm.dbitws import DbitWS
from dbitmm.ringbuffer import RingBuffer
import numpy as np


class StoikovMarketMaker:
    def __init__(self, gamma, k, sigma):
        self.gamma = gamma  # Risk aversion parameter
        self.k = k  # Order arrival intensity
        self.sigma = sigma  # Volatility

    def calculate_optimal_prices(self, mid_price, inventory):
        reservation_price = mid_price - (self.gamma * self.sigma**2 * inventory) / self.k
        spread = self.gamma * self.sigma**2 / self.k + (2/self.gamma) * np.log(1 + self.gamma/self.k)
        
        optimal_bid = reservation_price - spread/2
        optimal_ask = reservation_price + spread/2
        
        return optimal_bid, optimal_ask



class MarketMaker:
    def __init__(self, instrument, dbit_ws, buffer_size=100):
        self.instrument = instrument
        self.dbit_ws = DbitWS()
        self.stoikov = StoikovMarketMaker(gamma=0.1, k=1.5, sigma=0.2)
        self.inventory = 0
        self.mid_price = None
        self.price_buffer = RingBuffer(buffer_size)
        self.last_quote_time = 0
        self.quote_interval = 5  # Minimum time between requotes in seconds
        self.volatility_buffer = RingBuffer(16)  # Buffer for the last 16 volatility data points
        self.current_volatility = None
        self.volatility_range = None

    async def start(self):
        await self.dbit_ws.connect()
        await self.dbit_ws.subscribe_channels(
            [f"book.{self.instrument}.100ms", f"user.trades.{self.instrument}.raw"],
            [f"user.orders.{self.instrument}.raw"]
        )
        asyncio.create_task(self.process_market_data())
        asyncio.create_task(self.update_orders())



    async def process_volatility_index_message(self, message):
        print("Processing volatility index message:", message)
        if 'params' in message and 'data' in message['params']:
            data = message['params']['data']
            volatility = data.get('volatility')
            timestamp = data.get('timestamp')
            index_name = data.get('index_name')

            if volatility is not None:
                self.volatility_buffer.append(volatility)
                self.current_volatility = volatility

                if self.volatility_buffer.is_full:
                    avg_volatility = self.volatility_buffer.get_mean()
                    std_volatility = self.volatility_buffer.get_std()

                    lower_bound = avg_volatility - 2 * std_volatility
                    upper_bound = avg_volatility + 2 * std_volatility

                    self.volatility_range = (lower_bound, upper_bound)

                    print(f"Current Volatility: {self.current_volatility}")
                    print(f"Average Volatility (last 16): {avg_volatility}")
                    print(f"Volatility Range (2 std dev): {self.volatility_range}")

                # You can still update your volatility DataFrame if needed
                if self.volatility_df is None or self.volatility_df.is_empty():
                    self.volatility_df = pl.DataFrame({
                        "timestamp": pl.Series(dtype=pl.Int64),
                        "volatility": pl.Series(dtype=pl.Float64),
                        "index_name": pl.Series(dtype=pl.Utf8)
                    })

                # Update the existing row or add a new one
                if index_name in self.volatility_df['index_name'].to_list():
                    self.volatility_df = self.volatility_df.with_columns(
                        pl.when(pl.col("index_name") == index_name)
                        .then(volatility)
                        .otherwise(pl.col("volatility"))
                        .alias("volatility"),
                        pl.when(pl.col("index_name") == index_name)
                        .then(timestamp)
                        .otherwise(pl.col("timestamp"))
                        .alias("timestamp")
                    )
                else:
                    new_volatility = pl.DataFrame({
                        "timestamp": [timestamp],
                        "volatility": [volatility],
                        "index_name": [index_name]
                    })
                    self.volatility_df = pl.concat([self.volatility_df, new_volatility], how="vertical")

                print("Updated Volatility Index DataFrame:")
                print(self.volatility_df)

    # You might want to add a method to get the current volatility info
    def get_current_volatility_info(self):
        return {
            "current": self.current_volatility,
            "range": self.volatility_range
        }
    




    async def process_market_data(self):
        while True:
            message = await self.dbit_ws.message_queue.get()
            if message['method'] == 'subscription':
                channel = message['params']['channel']
                if channel.startswith('book.'):
                    await self.handle_orderbook(message['params']['data'])
                elif channel.startswith('user.trades.'):
                    await self.handle_trade(message['params']['data'])

    async def handle_orderbook(self, data):
        best_bid = data['bids'][0][0]
        best_ask = data['asks'][0][0]
        new_mid_price = (best_bid + best_ask) / 2
        
        if self.mid_price is not None:
            price_change = new_mid_price - self.mid_price
            self.price_buffer.append(price_change)
        
        self.mid_price = new_mid_price

    async def handle_trade(self, data):
        # Update inventory based on executed trades
        for trade in data:
            if trade['direction'] == 'buy':
                self.inventory += trade['amount']
            else:
                self.inventory -= trade['amount']

    def should_requote(self):
        current_time = asyncio.get_event_loop().time()
        if current_time - self.last_quote_time < self.quote_interval:
            return False
        
        if self.price_buffer.is_full:
            mean_change = self.price_buffer.get_mean()
            std_change = self.price_buffer.get_std()
            
            # Requote if the recent price changes are significant
            if abs(mean_change) > 2 * std_change:
                return True
        
        return False

    async def update_orders(self):
        while True:
            if self.mid_price is not None and self.should_requote():
                volatility_info = self.get_current_volatility_info()
                
                if volatility_info['current'] is not None and volatility_info['range'] is not None:
                    current_vol = volatility_info['current']
                    lower_bound, upper_bound = volatility_info['range']
                    
                    # Adjust the Stoikov parameters based on volatility
                    if current_vol < lower_bound:
                        # Lower volatility, tighten spreads
                        self.stoikov.gamma *= 0.9
                    elif current_vol > upper_bound:
                        # Higher volatility, widen spreads
                        self.stoikov.gamma *= 1.1
                    
                    # Ensure gamma stays within reasonable bounds
                    self.stoikov.gamma = max(0.05, min(0.5, self.stoikov.gamma))
                
                optimal_bid, optimal_ask = self.stoikov.calculate_optimal_prices(self.mid_price, self.inventory)
                
                # Cancel existing orders and place new ones
                await self.dbit_ws.cancel_all_orders(self.instrument)
                await self.dbit_ws.place_buy(self.instrument, amount=10, order_type="limit", label="stoikov_bid", price=optimal_bid)
                await self.dbit_ws.place_sell(self.instrument, amount=10, order_type="limit", label="stoikov_ask", price=optimal_ask)
                
                self.last_quote_time = asyncio.get_event_loop().time()
            
            await asyncio.sleep(1)  # Check conditions every second

    async def shutdown(self):
        # Logic to cleanly shut down the market maker
        print("Shutting down MarketMaker...")
        await self.dbit_ws.cancel_all_orders()  # Example of cleaning up
        # Add any other cleanup logic as needed




async def main():
    dbit_ws = DbitWS()
    market_maker = MarketMaker("BTC-PERPETUAL", dbit_ws)
    await market_maker.start()

if __name__ == "__main__":
    asyncio.run(main())