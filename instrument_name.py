import requests
import yaml
import asyncio
import websockets
import json

def load_parameters(file_path='parameters.yaml'):
    """
    Load parameters from the YAML configuration file.
    """
    with open(file_path, 'r') as file:
        parameters = yaml.safe_load(file)
    return parameters

async def fetch_instruments(currency, kind):
    """
    Fetch instruments from Deribit for a specified currency and kind.
    """
    msg = {
        "method": "public/get_instruments",
        "params": {
            "currency": currency,
            "kind": kind
        },
        "jsonrpc": "2.0",
        "id": 1
    }

    async with websockets.connect('wss://www.deribit.com/ws/api/v2', max_size=2**20) as websocket:
        await websocket.send(json.dumps(msg))
        response = await websocket.recv()
        return json.loads(response)

async def get_all_instruments():
    """
    Fetch all instruments for the currencies and kinds specified in the parameters.yaml file.
    """
    # Load parameters from YAML
    params = load_parameters()
    currencies = params['deribit']['currencies']
    kinds = params['deribit']['kinds']

    # Create an empty list to store results
    all_instruments = []

    for currency in currencies:
        for kind in kinds:
            response = await fetch_instruments(currency, kind)
            # Process the response to extract instrument details
            instruments = response.get('result', [])
            # Extract relevant fields from each instrument
            for instrument in instruments:
                instrument_data = {
                    "currency": currency,
                    "kind": kind,
                    "instrument_name": instrument.get("instrument_name"),
                    "min_trade_amount": instrument.get("min_trade_amount"),
                    "tick_size": instrument.get("tick_size"),
                    "min_trade_amount": instrument.get("min_trade_amount"),
                    "contract_size": instrument.get("contract_size"),
                    "taker_commission": instrument.get("taker_commission"),
                    "maker_commission": instrument.get("maker_commission")
                }
                all_instruments.append(instrument_data)

    return all_instruments

if __name__ == "__main__":
    asyncio.run(get_all_instruments())