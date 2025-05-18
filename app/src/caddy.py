import os
import re
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

def create_vhost(username: str, server: str, ip_prefix: int, hashed_password: str):
    fqdn = f"{username}.{server}.hikka.host"
    target_ip = f"192.168.{ip_prefix}.101"

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


def remove_caddy_user(username, server):
    config_path = Path(CADDY_CONFIG_PATH) / f"{username}.{server}.caddy"
    if config_path.exists():
        config_path.unlink()
        reload_caddy()
    else:
        print(f"Configuration for {username}.{server} does not exist.")


def update_password(username: str, server: str, hashed_password: str):
    config_path = Path(CADDY_CONFIG_PATH) / f"{username}.{server}.caddy"
    if config_path.exists():
        config = config_path.read_text()
        regex = r"basicauth\s*{\s*.*?\s*}"
        config = re.sub(regex, "", config, flags=re.DOTALL)
        config += f"    basicauth {{\n        {username} {hashed_password}\n    }}\n"
        config_path.write_text(config)
        reload_caddy()
    else:
        print(f"Configuration for {username}.{server} does not exist.")


def reload_caddy():
    os.system("caddy reload")
