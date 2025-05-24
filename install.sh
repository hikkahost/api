#!/bin/bash

# Проверяем, что скрипт выполняется от root
if [ "$(id -u)" -ne 0 ]; then
  echo "Этот скрипт должен быть запущен с правами root."
  exit 1
fi

# Запрос имени сервера
read -p "Введите имя сервера (например, m1): " SERVER_NAME

# Проверка пустого ввода
if [ -z "$SERVER_NAME" ]; then
  echo "Имя сервера не может быть пустым."
  exit 1
fi

# Порт API
API_PORT=8000

# Шаг 1: Обновление и установка зависимостей
echo "Обновление системы и установка зависимостей..."
apt update -y
apt install -y software-properties-common wget git apt-transport-https ca-certificates curl gnupg2

# Шаг 2: Добавление репозитория и установка Python 3.8 и docker
echo "Добавление репозитория и установка Python 3.8 и docker..."
add-apt-repository ppa:deadsnakes/ppa -y
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable"
apt update -y
apt install -y python3.8 python3.8-distutils python3.8-venv docker-ce

# Шаг 3: Установка pip и виртуального окружения
echo "Установка pip и виртуального окружения..."
wget https://bootstrap.pypa.io/get-pip.py
python3.8 get-pip.py
python3.8 -m pip install virtualenv

# Шаг 4: Клонирование репозитория API
echo "Клонирование репозитория API..."
git clone -b dev https://github.com/hikkahost/api /root/api
cd /root/api

# Шаг 5: Создание виртуального окружения и установка зависимостей
echo "Создание виртуального окружения и установка зависимостей..."
python3.8 -m venv venv
source venv/bin/activate
python3.8 -m pip install -r requirements.txt

# Шаг 6: Выполнение тестов
echo "Запуск тестов..."
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
python3.8 -m pytest

# Шаг 7: Генерация секретного ключа
SECRET_KEY=$(openssl rand -base64 32)
echo "Секретный ключ сгенерирован: $SECRET_KEY"

# Шаг 8: Создание окончательной конфигурации
echo "Создание конфигурационного файла..."
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

# Шаг 9: Установка Caddy
echo "Установка Caddy..."
apt install -y debian-keyring debian-archive-keyring
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt update
apt install -y caddy

# Шаг 10: Настройка директорий и конфигов Caddy
echo "Настройка Caddy..."
mkdir -p /etc/caddy/conf.d

cat <<EOL > /etc/caddy/conf.d/api.$SERVER_NAME.hikka.host.caddy
api.$SERVER_NAME.hikka.host {
    reverse_proxy 127.0.0.1:$API_PORT
}
EOL

cat <<EOL > /etc/caddy/Caddyfile
import /etc/caddy/conf.d/*.caddy
EOL

chown -R root:caddy /etc/caddy
chmod -R 755 /etc/caddy

# Шаг 11: Перезапуск и включение Caddy
systemctl enable caddy
systemctl restart caddy

# Шаг 12: Создание systemd-сервиса для API
echo "Создание systemd сервиса для API..."
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

# Шаг 13: Запуск API
echo "Запуск API службы..."
systemctl daemon-reload
systemctl enable api.service
systemctl start api.service

# Шаг 14: Финальный вывод
IP_ADDRESS=$(hostname -I | awk '{print $1}')
echo "✅ API запущен: http://api.$SERVER_NAME.hikka.host → $IP_ADDRESS:$API_PORT"
echo "🔑 Секретный ключ: $SECRET_KEY"
