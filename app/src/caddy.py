import os
import re
import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

CADDY_CONFIG_PATH = "/etc/caddy/conf.d"
CADDY_LOG_DIR = "/var/log/caddy"
BASIC_AUTH_MARKER = "# BASIC_AUTH"
SETUP_WEB_UPSTREAM = "127.0.0.1:8001"

CADDYFILE_TEMPLATE = """
{fqdn} {{
    tls /etc/ssl/cloudflare-origin.crt /etc/ssl/cloudflare-origin.key

    header {{
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
        Permissions-Policy "geolocation=(), microphone=(), camera=()"
        Content-Security-Policy "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self'; img-src 'self' data:; connect-src 'self'"
    }}

    log {{
        output file {log_dir}/hikka-{username}.log
        format json
    }}

    @sensitive {{
        path *.session
        path *.lock
        path /config.json
        path_regexp per_user_config `config-[0-9]+\\.json$`
        path /.env
    }}
    respond @sensitive 404

    handle {{
        {basic_auth_marker}
        basic_auth {{
            {username} "{hashed_password}"
        }}
        reverse_proxy {setup_upstream} {{
            header_up X-Hikkahost-Container {username}
            header_up X-Real-IP {{remote_host}}
            header_up X-Forwarded-For {{remote_host}}
            header_up X-Forwarded-Proto {{scheme}}
            header_up Host {{host}}
            header_up -Authorization
        }}
    }}
}}
"""


def read_vhost_password(username: str, server: str) -> Optional[str]:
    config_path = Path(CADDY_CONFIG_PATH) / f"{username}.{server}.caddy"
    if not config_path.exists():
        return None
    return _extract_existing_password(config_path.read_text(), username)


def _extract_existing_password(config: str, username: str) -> Optional[str]:
    pattern = re.compile(
        rf"basic_?auth\s*\{{\s*{re.escape(username)}\s+\"([^\"]+)\"",
        re.MULTILINE,
    )
    match = pattern.search(config)
    if not match:
        return None
    return match.group(1)


def _render_vhost(
    fqdn: str,
    username: str,
    hashed_password: str,
) -> str:
    os.makedirs(CADDY_LOG_DIR, exist_ok=True)
    return CADDYFILE_TEMPLATE.format(
        fqdn=fqdn,
        username=username,
        hashed_password=hashed_password,
        basic_auth_marker=BASIC_AUTH_MARKER,
        log_dir=CADDY_LOG_DIR,
        setup_upstream=SETUP_WEB_UPSTREAM,
    )


def create_vhost(username: str, server: str, ip_prefix: int, hashed_password: str):
    fqdn = f"{username}.{server}.hikka.host"
    config_path = Path(CADDY_CONFIG_PATH) / f"{username}.{server}.caddy"
    if config_path.exists():
        config = config_path.read_text()
        existing_password = _extract_existing_password(config, username)
        if not existing_password:
            print(
                f"Configuration for {username}.{server} exists but could not be upgraded."
            )
            return
        needs_upgrade = (
            SETUP_WEB_UPSTREAM not in config
            or ":8080" in config
            or "forward_auth" in config
            or "rate_limit" in config
            or "import ssl_dns" in config
            or "basicauth" in config
            or "/etc/ssl/cloudflare-origin.crt" not in config
            or "Strict-Transport-Security" not in config
            or "@sensitive" not in config
        )
        if not needs_upgrade:
            print(f"Configuration for {username}.{server} already exists.")
            return
        config = _render_vhost(fqdn, username, existing_password)
        config_path.write_text(config)
        reload_caddy()
        return

    config = _render_vhost(fqdn, username, hashed_password)
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
        "        basic_auth {\n"
        f'            {username} "{hashed_password}"\n'
        "        }\n"
    )
    new_auth_block_root = (
        "    basic_auth {\n" f'        {username} "{hashed_password}"\n' "    }\n"
    )

    marker_pattern = re.compile(rf"(?m)^\s*{re.escape(BASIC_AUTH_MARKER)}\s*$")
    if marker_pattern.search(config):
        marker_replace = re.compile(
            rf"(?ms)(^\s*{re.escape(BASIC_AUTH_MARKER)}\s*$)(?:\n\s*basic_?auth\s*\{{[^}}]*\}}\s*)?"
        )
        config = marker_replace.sub(rf"\1\n{new_auth_block_handle}", config, count=1)
    else:
        config = re.sub(r"(?m)^\s*basic_?auth\s*\{[^}]*\}\s*", "", config)
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
    if subprocess.run(["systemctl", "is-active", "--quiet", "caddy"]).returncode == 0:
        subprocess.run(["systemctl", "reload", "caddy"], check=False)
    else:
        subprocess.run(["systemctl", "start", "caddy"], check=False)
