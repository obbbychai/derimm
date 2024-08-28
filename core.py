from config import Config, get_env_variables

class Core:
    def __init__(self):
        self.config = Config()
        self.env_variables = get_env_variables()

    def get_pairs(self):
        return self.config.get_pairs()

    def get_tuning_strategy(self):
        return self.config.get_tuning_strategy()

    def get_env_variables(self):
        return self.env_variables