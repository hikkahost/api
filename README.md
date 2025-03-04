# hikkahost_api

```
docker pull vsecoder/hikka:latest # https://hub.docker.com/r/vsecoder/hikka
```

Change in ```config.py``` the ```SECRET_KEY``` and IP.

## Config

```python
CONTAINER = {
    "cpu_period": 50000,
    "cpu_quota": 25000,
    "mem_limit": "3g",
    "ip": "..."
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
    SECRET_KEY = "..."
```