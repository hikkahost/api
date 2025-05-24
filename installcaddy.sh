API_PORT=8000

read -p "Введите имя сервера (например, m1): " SERVER_NAME

if [ -z "$SERVER_NAME" ]; then
  echo "Имя сервера не может быть пустым."
  exit 1
fi

echo "Установка Caddy..."
sudo apt install -y debian-keyring debian-archive-keyring
sudo apt install libnss3-tools -y
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy

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

sudo chown -R root:caddy /etc/caddy
sudo chmod -R 755 /etc/caddy

sudo systemctl enable caddy
sudo systemctl restart caddy

source venv/bin/activate
python3.8 reinitcaddy.py
