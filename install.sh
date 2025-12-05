#!/bin/bash

# Проверяем, что скрипт выполняется от root
if [ "$(id -u)" -ne 0 ]; then
  echo "Этот скрипт должен быть запущен с правами root."
  exit 1
fi

# Запрос имени сервера
read -p "Введите имя сервера (например, m1): " SERVER_NAME

if [ -z "$SERVER_NAME" ]; then
  echo "Имя сервера не может быть пустым."
  exit 1
fi

# Запрос CF_Token
read -p "Введите Cloudflare API Token (CF_Token): " CF_TOKEN
if [ -z "$CF_TOKEN" ]; then
  echo "CF_Token не может быть пустым."
  exit 1
fi

# Порт API
API_PORT=8000

echo "Обновление системы и установка зависимостей..."
apt update -y
apt install -y software-properties-common wget git apt-transport-https ca-certificates curl gnupg2 libnss3-tools vnstat

echo "Добавление репозитория и установка Python 3.8 и docker..."
add-apt-repository ppa:deadsnakes/ppa -y
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable"
apt update -y
apt install -y python3.8 python3.8-distutils python3.8-venv docker-ce

echo "Установка pip и виртуального окружения..."
wget https://bootstrap.pypa.io/get-pip.py
python3.8 get-pip.py
python3.8 -m pip install virtualenv

echo "Клонирование репозитория API..."
git clone -b main https://github.com/hikkahost/api /root/api
cd /root/api

echo "Создание виртуального окружения и установка зависимостей..."
python3.8 -m venv venv
source venv/bin/activate
python3.8 -m pip install -r requirements.txt

echo "Создание тестовой конфигурации..."
cat <<EOL > /root/api/app/config.py
CONTAINER = {
    "cpu": 1.0,
    "memory": "512M",
    "size": "3g",
    "rate": "50mbit",
    "burst": "32kbit",
    "latency": "400ms",
}

SERVER = "$SERVER_NAME"

class Config:
    SECRET_KEY = "secret"
EOL

echo "Запуск тестов..."
python3.8 -m pytest

echo "Генерация секретного ключа..."
SECRET_KEY=$(openssl rand -base64 32)
echo "Секретный ключ: $SECRET_KEY"

echo "Создание финальной конфигурации..."
rm /root/api/app/config.py
cat <<EOL > /root/api/app/config.py
CONTAINER = {
    "cpu": 1.0,
    "memory": "512M",
    "size": "3g",
    "rate": "50mbit",
    "burst": "32kbit",
    "latency": "400ms",
}

SERVER = "$SERVER_NAME"

class Config:
    SECRET_KEY = "$SECRET_KEY"
EOL

echo "Установка Caddy..."
apt install -y debian-keyring debian-archive-keyring
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt update
apt install -y caddy

echo "Настройка директорий Caddy..."
mkdir -p /etc/caddy/conf.d

cat <<EOL > /etc/caddy/conf.d/api.$SERVER_NAME.hikka.host.caddy
api.$SERVER_NAME.hikka.host {
    reverse_proxy 127.0.0.1:$API_PORT
}
EOL

cat <<EOL > /etc/caddy/Caddyfile
(ssl_dns) {
  tls /etc/ssl/cloudflare-origin.crt /etc/ssl/cloudflare-origin.key
}

import /etc/caddy/conf.d/*.caddy
EOL

chown -R root:caddy /etc/caddy
chmod -R 755 /etc/caddy

systemctl enable caddy
systemctl restart caddy

echo "Создание systemd-сервиса API..."
cat <<EOL > /etc/systemd/system/api.service
[Unit]
Description=docker api
After=network.target

[Service]
WorkingDirectory=/root/api
ExecStart=/root/api/venv/bin/python3.8 -m app
Type=simple
Restart=always
RestartSec=1
User=root

[Install]
WantedBy=multi-user.target
EOL

systemctl daemon-reload
systemctl enable api.service
systemctl start api.service

echo "Установка cron и acme.sh..."
apt install cron -y
systemctl enable --now cron

curl https://get.acme.sh | sh
export CF_Token="$CF_TOKEN"

~/.acme.sh/acme.sh --register-account -m dev.fajox@gmail.com

~/.acme.sh/acme.sh --issue --dns dns_cf -d $SERVER_NAME.hikka.host -d "*.$SERVER_NAME.hikka.host"

~/.acme.sh/acme.sh --install-cert -d $SERVER_NAME.hikka.host \
  --key-file       /etc/ssl/cloudflare-origin.key \
  --fullchain-file /etc/ssl/cloudflare-origin.crt \
  --reloadcmd     "systemctl reload caddy"

chown caddy:caddy /etc/ssl/cloudflare-origin.crt
chown caddy:caddy /etc/ssl/cloudflare-origin.key
chmod 640 /etc/ssl/cloudflare-origin.*
systemctl restart caddy

echo "Добавление cron задач..."

(crontab -l 2>/dev/null; echo '27 12 * * * "/root/.acme.sh"/acme.sh --cron --home "/root/.acme.sh" > /dev/null') | crontab -

(crontab -l 2>/dev/null; echo '0 0 * * * /bin/bash -c '\''for tag in hikka heroku legacy geektg; do docker pull fajox/hikkahost:$tag >/dev/null 2>&1; done; docker image prune -a -f >/dev/null 2>&1'\''') | crontab -

(crontab -l 2>/dev/null; echo '0 0 * * 1 /sbin/reboot') | crontab -

IP_ADDRESS=$(hostname -I | awk '{print $1}')
echo "API запущен: http://api.$SERVER_NAME.hikka.host → $IP_ADDRESS:$API_PORT"
echo "Секретный ключ: $SECRET_KEY"
