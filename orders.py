import time
import os
import requests
import urllib.parse
import hashlib
import hmac
import base64
from dotenv import load_dotenv

load_dotenv()

# Read Kraken API key and secret stored in environment variables
api_url = "https://api.kraken.com"
api_key = os.environ['API_KEY_KRAKEN']
api_sec = os.environ['API_SEC_KRAKEN']

class KrakenOrders:
    def __init__(self):
        self.api_url = api_url
        self.api_key = api_key
        self.api_sec = api_sec

    # Attaches auth headers and returns results of a POST request
    def kraken_request(self, uri_path, data):
        headers = {
            'API-Key': self.api_key,
            'API-Sign': self.get_kraken_signature(uri_path, data, self.api_sec)
        }
        req = requests.post((self.api_url + uri_path), headers=headers, data=data)
        return req.json()

    def get_kraken_signature(self, urlpath, data, secret):
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()

    # Method to add an order
    def add_order(self, ordertype, type, volume, pair, price):
        response = self.kraken_request('/0/private/AddOrder', {
            "nonce": str(int(1000 * time.time())),
            "ordertype": ordertype,
            "type": type,
            "volume": volume,
            "pair": pair,
            "price": price
        })
        print("Add Order Response:", response)
        return response

    # Method to cancel an order
    def cancel_order(self, txid):
        response = self.kraken_request('/0/private/CancelOrder', {
            "nonce": str(int(1000 * time.time())),
            "txid": txid
        })
        print("Cancel Order Response:", response)
        return response

    # Method to edit an order
    def edit_order(self, txid, volume, pair, price, price2=None):
        data = {
            "nonce": str(int(1000 * time.time())),
            "txid": txid,
            "volume": volume,
            "pair": pair,
            "price": price
        }
        if price2 is not None:
            data["price2"] = price2
        
        response = self.kraken_request('/0/private/EditOrder', data)
        print("Edit Order Response:", response)
        return response

# Example usage
if __name__ == "__main__":
    orders = KrakenOrders()
    
    # Add an order
    add_response = orders.add_order("limit", "buy", 1.25, "XBTUSD", 27500)
    
    # Cancel an order (replace with a valid txid)
    # cancel_response = orders.cancel_order("OG5V2Y-RYKVL-DT3V3B")
    
    # Edit an order (replace with a valid txid)
    # edit_response = orders.edit_order("OHYO67-6LP66-HMQ437", 1.25, "XBTUSD", 27500, 26500)