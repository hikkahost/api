# import os
# from dotenv import load_dotenv

# load_dotenv()

CONTAINER = {
    # docker params
    "cpu": 1.0,
    "memory": "512M",
    "size": "3g",
    # network params
    "rate": "50mbit",
    "burst": "32kbit",
    "latency": "400ms",
}

class Config:
    SECRET_KEY = "secret"
