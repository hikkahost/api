import os
import bcrypt
from pathlib import Path

CADDY_CONFIG_PATH = "/etc/caddy/conf.d"
CADDYFILE_TEMPLATE = """
{fqdn} {{
    reverse_proxy {target_ip}:8080
    basicauth {{
        {username} {hashed_password}
    }}
}}
"""


def generate_hashed_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def create_vhost(username: str, server: str, ip_prefix: int, password: str):
    fqdn = f"{username}.{server}.hikka.host"
    target_ip = f"192.168.{ip_prefix}.101"
    hashed_password = generate_hashed_password(password)

    config = CADDYFILE_TEMPLATE.format(
        fqdn=fqdn,
        target_ip=target_ip,
        username=username,
        hashed_password=hashed_password,
    )

    os.makedirs(CADDY_CONFIG_PATH, exist_ok=True)
    config_path = Path(CADDY_CONFIG_PATH) / f"{username}.{server}.caddy"
    config_path.write_text(config)

    reload_caddy()


def reload_caddy():
    os.system("caddy reload")
