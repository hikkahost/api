import os
#from dotenv import load_dotenv

#load_dotenv()

CONTAINER = {
    "cpu_period": 50000,
    "cpu_quota": 25000,
    "mem_limit": "1g",
    "image": "hikka:latest",
    "ip": ""
}

class Config:
    SECRET_KEY = "secret"