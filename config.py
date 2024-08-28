from dotenv import load_dotenv
import os
import yaml

# Load environment variables from .env file
load_dotenv()

# Access environment variables and set them as constants
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
DERIBIT_URL = os.getenv('DERIBIT_URL')
HTX_WS_URL = os.getenv('HUOBI_WS_URL')
HTX_API_KEY = os.getenv('HUOBI_ID')
HTX_SECRET_KEY = os.getenv('HUOBI_SECRET')
API_KEY_KRAKEN = os.getenv('API_KEY_KRAKEN')
API_SEC_KRAKEN = os.getenv('API_SEC_KRAKEN')

class Config:
    def __init__(self, config_file='parameters.yaml'):
        self.config_file = config_file
        self.settings = self.load_config()

    def load_config(self):
        with open(self.config_file, 'r') as file:
            return yaml.safe_load(file)

    def get_pairs(self):
        return self.settings.get('pairs', [])

    def get_tuning_strategy(self):
        return self.settings.get('tuning_strategy', {})

# Optionally, you can create a function to get all environment variables
def get_env_variables():
    return {
        "CLIENT_ID": CLIENT_ID,
        "CLIENT_SECRET": CLIENT_SECRET,
        "DERIBIT_URL": DERIBIT_URL,
        "HTX_WS_URL": HTX_WS_URL,
        "HTX_API_KEY": HTX_API_KEY,
        "HTX_SECRET_KEY": HTX_SECRET_KEY,
        "API_KEY_KRAKEN": API_KEY_KRAKEN,
        "API_SEC_KRAKEN": API_SEC_KRAKEN,
    }