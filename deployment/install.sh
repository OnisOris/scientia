
#!/bin/bash
set -e
cd "$(dirname "$0")"

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

if [ "$EUID" -ne 0 ]; then
  echo "Пожалуйста, запускайте скрипт с sudo."
  exit 1
fi


echo "Выберите версию Python для виртуального окружения:"
echo "1) 3.10"
echo "2) 3.11"
echo "3) 3.12"
echo "4) 3.13"
read -p "Введите номер [1-4]: " PY_VER_CHOICE

case "$PY_VER_CHOICE" in
    1) PYTHON_VER="3.10" ;;
    2) PYTHON_VER="3.11" ;;
    3) PYTHON_VER="3.12" ;;
    4) PYTHON_VER="3.13" ;;
    *) echo "Неверный выбор. Прерывание установки."; exit 1 ;;
esac

echo "Используется Python версии $PYTHON_VER"

REAL_USER=$(logname)
REAL_HOME=$(eval echo "~$REAL_USER")
REAL_PATH="$REAL_HOME/.local/bin:$PATH"
NAME_APP="scientia" 
INSTALL_DIR="$REAL_HOME/scientia"
VENV_DIR="$INSTALL_DIR/.venv"


echo "Пользователь: $REAL_USER"
echo "Домашняя директория: $REAL_HOME"

read -p "Загружать в папку проекта docker-compose файл и запустить контейнер c postgress?\ 0 - да \другое - нет " CHOICE
if [[ "$CHOICE" == "0" ]]; then
    echo "Устанавливаем контейнер с postgress"
    sudo -u "$REAL_USER" env PATH="$REAL_PATH" wget https://raw.githubusercontent.com/OnisOris/scientia/refs/heads/main/deployment/docker-compose.yaml -O $INSTALL_DIR && docker compose up -d
fi


if sudo -u "$REAL_USER" env PATH="$REAL_PATH" bash -c 'command -v uv &>/dev/null'; then
    echo "✅ uv уже установлен. Установка не требуется."
else
    echo "🔧 uv не найден. Устанавливаю..."
    sudo -u "$REAL_USER" bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
fi


echo "Создаём директорию $INSTALL_DIR..."
sudo -u "$REAL_USER" mkdir -p "$INSTALL_DIR"

echo "Создаём виртуальное окружение..."
sudo -u "$REAL_USER" env PATH="$REAL_PATH" bash -c "\"$REAL_HOME/.local/bin/uv\" venv --python $PYTHON_VER --prompt $NAME_APP \"$VENV_DIR\""

sudo -u "$REAL_USER" env PATH="$REAL_PATH" bash -c "source \"$VENV_DIR/bin/activate\" && \"$REAL_HOME/.local/bin/uv\" pip install \"git+https://github.com/OnisOris/scientia\""

echo "Создаём systemd unit файл /etc/systemd/system/scientia.service..."

cat > /etc/systemd/system/scientia.service << EOF
[Unit]
Description=$NAME_APP Autostart Service
After=network.target

[Service]
Type=simple
ExecStart=$VENV_DIR/bin/python -m scientia-app
WorkingDirectory=$INSTALL_DIR
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
User=$REAL_USER

[Install]
WantedBy=multi-user.target
EOF

cat > $REAL_HOME/$NAME_APP/.env << EOF
DB_USER=sciuser
DB_PASS=sci_password
DB_HOST=localhost
DB_PORT=5434
DB_NAME=scientia_db
API_URL=http://localhost:8000
TG_BOT_TOKEN=YOUR_TOKEN
ADMIN_SECRET=your-super-admin-secret-key
ADMIN_IDS=your_admin_tg_id
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SECRET_KEY="your-super-secret-key"
ALGORITHM="HS256"
EOF

echo "Перезагружаем systemd"
systemctl daemon-reexec
systemctl daemon-reload
systemctl enable $NAME_APP.service
systemctl restart $NAME_APP.service

echo "✅ Установка завершена. "
echo "Сервис '$NAME_APP.service' доступен под пользователем $REAL_USER." 
echo "Измените конфиг файл в .env, после введите команду:"
echo "systemctl restart $NAME_APP.service"
