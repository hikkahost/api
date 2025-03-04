import os
# from dotenv import load_dotenv

# load_dotenv()

CONTAINER = {
    "cpu_period": 50000,
    "cpu_quota": 25000,
    "mem_limit": "3g",
    "ip": "",
}

SUPPORTED_USERBOTS = [
    "hikka",
    "heroku"
]

USERBOTS = {
    "hikka": "vsecoder/hikka:latest",
    "heroku": "vsecoder/hikka:fork-codrago"
}

class Config:
    SECRET_KEY = "secret"
