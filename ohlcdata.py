import requests
import polars as pl
import numpy as np

def fetch_ohlc_data(pair, interval=1):
    """
    Fetch OHLC data from Kraken for a specified trading pair.

    :param pair: The trading pair (e.g., 'XBTUSD').
    :param interval: The interval for the candlestick data (1, 5, 15, 30, 60, 240, 1440, 10080, 21600).
    :return: A Polars DataFrame containing the OHLC data.
    """
    url = f'https://api.kraken.com/0/public/OHLC?pair={pair}&interval={interval}'
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if data['result']:
            # Extract the OHLC data
            ohlc_data = data['result'][pair]
            # Create a Polars DataFrame
            df = pl.DataFrame(ohlc_data, schema=["time", "open", "high", "low", "close", "vwap", "volume", "count"])
            return df
        else:
            print(f"No data found for the specified pair: {pair}.")
    else:
        print(f"Error fetching data for {pair}: {response.status_code}")
    
    return None

def calculate_volatility(df):
    """
    Calculate the volatility based on the closing prices.

    :param df: A Polars DataFrame containing OHLC data.
    :return: The volatility as a float.
    """
    if df is not None and not df.is_empty():
        # Convert the 'close' column to float
        close_prices = df['close'].cast(pl.Float64).to_numpy()
        # Calculate the standard deviation of the closing prices
        volatility = np.std(close_prices)
        return volatility
    return None

# Example usage
if __name__ == "__main__":
    pair = "USDCCAD"  # Specify the trading pair
    intervals = [1, 5, 15, 30, 60, 240]  # Specify the intervals (1 min to 4 hours)
    
    for interval in intervals:
        ohlc_df = fetch_ohlc_data(pair, interval)
        if ohlc_df is not None:
            print(f"OHLC Data for {pair} at {interval} minutes:")
            print(ohlc_df)
            volatility = calculate_volatility(ohlc_df)
            print(f"Volatility for {interval} minutes: {volatility:.6f}\n")