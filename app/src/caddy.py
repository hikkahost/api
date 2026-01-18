import os
import re
import subprocess
from typing import Optional
from pathlib import Path

CADDY_CONFIG_PATH = "/etc/caddy/conf.d"
AUTH_API_URL = os.environ.get("HIKKAHOST_AUTH_API_URL", "https://beta.api.hikka.host").rstrip("/")
BASIC_AUTH_MARKER = "# BASIC_AUTH"
CADDYFILE_TEMPLATE = """
{fqdn} {{
    import ssl_dns

    @init_data_header {{
        header X-Telegram-Init-Data *
    }}

    @init_data_query {{
        query init_data=*
    }}

    handle @init_data_header {{
        forward_auth {auth_api_url} {{
            uri /test
            header_up X-Telegram-Init-Data {{http.request.header.X-Telegram-Init-Data}}
        }}
        reverse_proxy {target_ip}:8080
    }}

    handle @init_data_query {{
        forward_auth {auth_api_url} {{
            uri /test
            header_up X-Telegram-Init-Data {{http.request.uri.query.init_data}}
        }}
        reverse_proxy {target_ip}:8080
    }}

    handle {{
        {basic_auth_marker}
        basicauth {{
            {username} "{hashed_password}"
        }}
        reverse_proxy {target_ip}:8080
    }}
}}
"""


def _extract_existing_password(config: str, username: str) -> Optional[str]:
    pattern = re.compile(
        rf"basicauth\s*\{{\s*{re.escape(username)}\s+\"([^\"]+)\"",
        re.MULTILINE,
    )
    match = pattern.search(config)
    if not match:
        return None
    return match.group(1)


def _extract_existing_target_ip(config: str) -> Optional[str]:
    pattern = re.compile(r"reverse_proxy\s+([0-9.]+):8080", re.MULTILINE)
    match = pattern.search(config)
    if not match:
        return None
    return match.group(1)

def create_vhost(username: str, server: str, ip_prefix: int, hashed_password: str):
    fqdn = f"{username}.{server}.hikka.host"
    config_path = Path(CADDY_CONFIG_PATH) / f"{username}.{server}.caddy"
    if config_path.exists():
        config = config_path.read_text()
        existing_password = _extract_existing_password(config, username)
        target_ip = _extract_existing_target_ip(config)
        if not existing_password or not target_ip:
            print(
                f"Configuration for {username}.{server} exists but could not be upgraded."
            )
            return
        needs_upgrade = "query init_data" not in config and "@init_data_query" not in config
        if "forward_auth" in config or "@init_data" in config:
            if not needs_upgrade:
                print(f"Configuration for {username}.{server} already exists.")
                return
        config = CADDYFILE_TEMPLATE.format(
            fqdn=fqdn,
            target_ip=target_ip,
            username=username,
            hashed_password=existing_password,
            auth_api_url=AUTH_API_URL,
            basic_auth_marker=BASIC_AUTH_MARKER,
        )
        config_path.write_text(config)
        reload_caddy()
        return

    target_ip = f"192.168.{ip_prefix}.101"

    config = CADDYFILE_TEMPLATE.format(
        fqdn=fqdn,
        target_ip=target_ip,
        username=username,
        hashed_password=hashed_password,
        auth_api_url=AUTH_API_URL,
        basic_auth_marker=BASIC_AUTH_MARKER,
    )

    os.makedirs(CADDY_CONFIG_PATH, exist_ok=True)
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

    if not config_path.exists():
        print(f"Configuration for {username}.{server} does not exist.")
        return

    config = config_path.read_text()

    new_auth_block_handle = (
        "        basicauth {\n"
        f"            {username} \"{hashed_password}\"\n"
        "        }\n"
    )
    new_auth_block_root = (
        "    basicauth {\n"
        f"        {username} \"{hashed_password}\"\n"
        "    }\n"
    )

    marker_pattern = re.compile(
        rf"(?m)^\s*{re.escape(BASIC_AUTH_MARKER)}\s*$"
    )
    if marker_pattern.search(config):
        marker_replace = re.compile(
            rf"(?ms)(^\s*{re.escape(BASIC_AUTH_MARKER)}\s*$)(?:\n\s*basicauth\s*\{{[^}}]*\}}\s*)?"
        )
        config = marker_replace.sub(rf"\1\n{new_auth_block_handle}", config, count=1)
    else:
        config = re.sub(r"(?m)^\s*basicauth\s*\{[^}]*\}\s*", "", config)
        pattern = re.compile(
            rf"({username}\.{server}\.hikka\.host\s*\{{)", re.MULTILINE
        )
        config = pattern.sub(
            lambda match: f"{match.group(1)}\n{new_auth_block_root}",
            config,
            count=1,
        )

    config_path.write_text(config)
    reload_caddy()


def reload_caddy():
    subprocess.run(["systemctl", "restart", "caddy"], check=False)
