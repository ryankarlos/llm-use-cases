import json
import configparser

def load_rules():
    """Load red words rules from JSON file."""
    with open("rd_rules.json", "r") as file:
        return json.load(file)

def load_config():
    """Load configuration from INI file."""
    config = configparser.ConfigParser()
    config.read("rd_config.ini")
    return config
