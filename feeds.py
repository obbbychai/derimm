import asyncio
import yaml
from dbitmm.dbitws import DbitWS  # Import the DbitWS class
from event_bus import EventBus

class Data:
    def __init__(self):
        self.event_bus = EventBus()  # Initialize the event bus
        self.dbit_ws = DbitWS(self.event_bus)  # Create an instance of DbitWS

    async def connect(self):
        await self.dbit_ws.connect()  # Connect to the WebSocket

    async def load_config(self, config_file='parameters.yaml'):
        # Load all parameters from the configuration file
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)

        # Extract necessary parameters
        self.instrument_names = config.get('deribit', {}).get('currencies', [])
        self.instrument_details = config.get('deribit', {}).get('instrument_details', {})

    async def get_historical_volatility(self, currency):
        # Ensure the connection is established
        await self.connect()

        # Fetch historical volatility
        historical_volatility = await self.dbit_ws.get_historical_volatility(currency)

        # Process the result to calculate average volatility
        if historical_volatility and isinstance(historical_volatility, list):
            # Extract the values from the result
            values = [item[1] for item in historical_volatility]  # item[1] is the volatility value
            average_volatility = sum(values) / len(values) if values else 0  # Calculate average
            return average_volatility
        else:
            print("Error retrieving historical volatility:", historical_volatility)
            return None  # Return None or handle the error as needed

# Example usage
if __name__ == "__main__":
    async def main():
        data = Data()  # Create an instance of Data
        await data.load_config()  # Load configuration
        average_volatility = await data.get_historical_volatility("BTC")  # Get average historical volatility for BTC
        print("Average Historical Volatility:", average_volatility)

    asyncio.run(main())