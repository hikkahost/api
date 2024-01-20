import psutil


def bytes_to_megabytes(b: int) -> float:
    """
    Convert bytes to megabytes.

    :param b: Bytes.
    :return: Megabytes.
    """
    return round(b / 1024 / 1024, 1)


def get_server_resources() -> dict:
    """
    Get server resources.

    :return: Server resources.
    """
    return {
        "cpu_load_percent": psutil.cpu_percent(),
        "cpu_total": psutil.cpu_count(logical=True),
        "ram_load": bytes_to_megabytes(
            psutil.virtual_memory().total - psutil.virtual_memory().available
        ),
        "ram_load_percent": psutil.virtual_memory().percent,
        "ram_total": bytes_to_megabytes(psutil.virtual_memory().total),
    }
