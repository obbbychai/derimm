import asyncio
from dbitmm.dbitws import DbitWS
from mm import MM  # Adjust the import based on your file structure

async def main():
    dbit_ws = DbitWS()  # Create an instance of DbitWS
    market_maker = MM("BTC-16AUG24", dbit_ws)  # Create an instance of MM
    await market_maker.start()  # Start the market maker

if __name__ == "__main__":
    asyncio.run(main())  # Run the main function