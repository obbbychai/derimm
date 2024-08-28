import asyncio
from dbitws import DbitWS
import signal
import uuid
from calculations import calculate_stoikov
from ringbuffer import volBuffer
from oms import PendingOrderTracker, Order
from config import Config, DERIBIT_URL, CLIENT_ID, CLIENT_SECRET
from instrument_name import get_all_instruments

# Initialize the volatility buffer
volatility_buffer = volBuffer(size=16)  # Adjust size as needed
order_tracker = PendingOrderTracker()

# Load configuration
config = Config()
deribit_config = config.settings.get('deribit', {})

async def fetch_instrument_info():
    all_instruments = await get_all_instruments()
    # For this example, we'll use the first BTC future instrument
    btc_future = all_instruments[(all_instruments['currency'] == 'BTC') & (all_instruments['kind'] == 'future')].iloc[0]
    return btc_future['instrument_name'], btc_future['tick_size']

async def quoting_logic(dbitws, instrument_name, tick_size):
    while True:
        try:
            current_volatility = dbitws.current_volatility
            
            if current_volatility is not None:
                volatility_buffer.add(current_volatility)
                mean, upper_band, lower_band = volatility_buffer.bollinger_bands(period=16, num_std_dev=3)
                
                if lower_band is not None and upper_band is not None and lower_band <= current_volatility <= upper_band:
                    mid_price, spread, best_bid, best_ask, optimal_bid, optimal_ask = calculate_stoikov(
                        dbitws.order_book,
                        dbitws.inventory, 
                        current_volatility,
                        dbitws.risk_aversion,
                        dbitws.time_horizon,
                        tick_size=tick_size
                    )
                    
                    if optimal_bid is not None and optimal_ask is not None:
                        buy_order_id = str(uuid.uuid4())
                        sell_order_id = str(uuid.uuid4())
                        
                        await dbitws.place_buy(instrument_name=instrument_name, amount=10, order_type="limit", label="buy_order", price=optimal_bid)
                        await dbitws.place_sell(instrument_name=instrument_name, amount=10, order_type="limit", label="sell_order", price=optimal_ask)
                        
                        order_tracker.add_order(Order(id=buy_order_id, price=optimal_bid, quantity=10, side='buy', timestamp=0, instrument_name=instrument_name))
                        order_tracker.add_order(Order(id=sell_order_id, price=optimal_ask, quantity=10, side='sell', timestamp=0, instrument_name=instrument_name))
                        
                        print(f"Placed buy order at {optimal_bid} and sell order at {optimal_ask} for {instrument_name}")
                else:
                    print("Volatility outside of Bollinger Bands, skipping order placement")
            else:
                print("Current volatility is None, skipping order placement")
        except Exception as e:
            print(f"Error in quoting_logic: {e}")
        
        await asyncio.sleep(5) 

async def trade_monitor(dbitws):
    while True:
        pending_orders = order_tracker.get_all_pending_orders()
        
        for order in pending_orders:
            order_state = await dbitws.get_order_state(order.instrument_name, order.id)
            if order_state:
                order_tracker.update_order(order.id, status=order_state['order_state'])
                
                if order_state['order_state'] == 'filled':
                    print(f"Order {order.id} has been filled!")
                    # Implement your post-fill logic here
                elif order_state['order_state'] == 'cancelled':
                    print(f"Order {order.id} has been cancelled!")
                    order_tracker.remove_order(order.id)
        
        await asyncio.sleep(1)  # Check every second

async def main():
    dbitws = DbitWS()
    dbitws.client_id = CLIENT_ID
    dbitws.client_secret = CLIENT_SECRET
    dbitws.url = DERIBIT_URL
    dbitws.risk_aversion = deribit_config.get('risk_aversion', 0.5)
    dbitws.time_horizon = deribit_config.get('T', 1)
    dbitws.gamma = deribit_config.get('gamma', 0.1)
    dbitws.kappa = deribit_config.get('kappa', 1.5)
    dbitws.sigma = deribit_config.get('sigma', 0.01)
    
    await dbitws.connect()
    
    all_instruments = await get_all_instruments()
    
    # Find the first BTC future instrument
    btc_future = next((instrument for instrument in all_instruments
                       if instrument['currency'] == 'BTC' and instrument['kind'] == 'future'), None)
    
    if btc_future:
        instrument_name = btc_future['instrument_name']
        tick_size = btc_future['tick_size']
        print(f"Trading on instrument: {instrument_name} with tick size: {tick_size}")
    else:
        print("No BTC future instrument found.")
    
    public_channels = [
        f"book.{instrument_name}.raw", 
        f"quote.{instrument_name}", 
        "deribit_volatility_index.btc_usd",
    ]
    private_channels = [
        "user.changes.future.BTC.100ms",
        f"user.orders.{instrument_name}.raw",  # This channel is crucial for order updates
        "user.portfolio.btc"
    ]
    await dbitws.subscribe_channels(public_channels, private_channels)

    # Run the trade monitor and quoting logic concurrently
    monitor_task = asyncio.create_task(trade_monitor(dbitws))
    quoting_task = asyncio.create_task(quoting_logic(dbitws, instrument_name, tick_size))
    
    # Wait for both tasks to complete (which they won't, unless there's an error)
    await asyncio.gather(monitor_task, quoting_task)

async def shutdown(signal, loop):
    print(f"Received exit signal {signal.name}...")
    
    dbitws = DbitWS()
    try:
        await dbitws.connect()
        await dbitws.cancel_all_orders()
    except Exception as e:
        print(f"Error during shutdown: {e}")
    
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(shutdown(s, loop)))
    
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()