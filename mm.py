from dbitmm.dbitws import DbitWS


class MM:
    def __init__(self, instrument, dbit_ws):
        self.dbit_ws = dbit_ws  # Assign the passed dbit_ws to an instance variable


    async def start(self):
        await self.dbit_ws.connect()  # Use the instance variable
        public_channels = [
            "book.BTC-16AUG24.raw",
            "quote.BTC-16AUG24", 
            "chart.trades.BTC-16AUG24.15",
            "deribit_volatility_index.btc_usd",
        ]
        private_channels = [
            "user.changes.future.BTC.100ms",
            "user.portfolio.btc"
        ]

        # Subscribe to channels
        await self.dbit_ws.subscribe_channels(public_channels, private_channels)  # Use the instance variable