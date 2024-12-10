# hikkahost_api

!!! NEED PYTHON 3.8 !!!

```
docker pull vsecoder/hikka:latest # https://hub.docker.com/r/vsecoder/hikka
```

Change in ```config.py``` the ```SECRET_KEY```.

## Config

```python
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
```