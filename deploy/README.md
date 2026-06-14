# Развёртывание itnews_portal на VPS (Ubuntu, systemd + venv)

Скрипт запускается раз в день в 08:45 (Europe/Belgrade) через systemd-таймер,
собирает новости, строит расписание на 9:00–21:00 и постит их в Telegram
до последней публикации, после чего процесс завершается.

## 1. Подготовка сервера

```bash
sudo apt update
sudo apt install -y python3-venv git

# отдельный пользователь без shell-доступа
sudo useradd --system --create-home --shell /usr/sbin/nologin itnews
```

## 2. Установка проекта

```bash
sudo git clone https://github.com/captaintwin/itnews_portal.git /opt/itnews_portal
cd /opt/itnews_portal
sudo python3 -m venv venv
sudo venv/bin/pip install -r requirements.txt
sudo chown -R itnews:itnews /opt/itnews_portal
```

## 3. Секреты (.env)

Файл `.env` в репозиторий не попадает (`.gitignore`) — скопируйте его с рабочей
машины вручную, например:

```powershell
# с Windows-машины
scp F:\Py_Projects\itnews_portal\.env user@SERVER:/tmp/itnews.env
```

```bash
# на сервере
sudo mv /tmp/itnews.env /opt/itnews_portal/.env
sudo chown itnews:itnews /opt/itnews_portal/.env
sudo chmod 600 /opt/itnews_portal/.env
```

Ожидаемые переменные: `TELEGRAM_TOKEN`, `REPORT_TELEGRAM_TOKEN`, `TELEGRAM_CHAT`.

## 4. Установка systemd-юнитов

```bash
sudo cp /opt/itnews_portal/deploy/itnews.service /etc/systemd/system/
sudo cp /opt/itnews_portal/deploy/itnews.timer /etc/systemd/system/
sudo cp /opt/itnews_portal/deploy/itnews-watchdog.service /etc/systemd/system/
sudo cp /opt/itnews_portal/deploy/itnews-watchdog.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now itnews.timer itnews-watchdog.timer
```

## 5. Проверка

```bash
# когда сработает таймер
systemctl list-timers itnews.timer

# ручной тестовый запуск (только в окне 9:00–21:00 по Белграду,
# иначе расписание не создастся и скрипт выйдет)
sudo systemctl start itnews.service

# логи в реальном времени
journalctl -u itnews.service -f
```

## 6. Обновление кода

```bash
cd /opt/itnews_portal
sudo -u itnews git pull
sudo venv/bin/pip install -r requirements.txt
```

## Примечания

- `Restart` у сервиса намеренно отключён: при старте `main.py` удаляет
  `data/sent_news.json` и пересоздаёт расписание, поэтому авторестарт после
  падения привёл бы к дублям постов.
- `Persistent=true` у таймера: если сервер был выключен в 08:45, запуск
  произойдёт сразу после загрузки (расписание корректно строится в любое
  время внутри окна 9:00–21:00).
- **Watchdog** (`itnews-watchdog.timer`): через 3 мин после перезагрузки
  проверяет, был ли постинг сегодня; если нет и сейчас 08:50–21:00 —
  автоматически запускает `itnews.service`. В 10:15 — повторная проверка
  и алерт в техчат, если постов всё ещё нет. Авторестарт не срабатывает,
  если часть постов уже ушла (чтобы не было дублей).
- После успешного запуска на VPS отключите задачу Windows
  «Telegram Auto Poster» на старой машине, чтобы не было двойного постинга:

```powershell
Disable-ScheduledTask -TaskName "Telegram Auto Poster"
```
