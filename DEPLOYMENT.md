# 🚀 Деплой Uni-RAG на VPS

## Архитектура

GitHub → GitHub Actions → SSH → VPS → Docker Compose → [FastAPI + Next.js + PostgreSQL]

Nginx работает как reverse proxy с SSL (Let's Encrypt).

## Требования

- VPS с Ubuntu 22.04+ (2 vCPU, 4 GB RAM)
- Домен с A-записью на IP VPS
- Docker + Docker Compose

## Установка

### 1. Клонирование и запуск

```bash
cd /opt
git clone https://github.com/Viskarius/Universal-Hybrid-Local-RAG.git uni-rag
cd uni-rag
docker compose up -d --build


### 2. Настройка Nginx

Создаём конфиг reverse proxy:

```bash
cat > /etc/nginx/sites-available/uni-rag << 'EOF'
server {
    listen 80;
    server_name test-demo-sys4tec.ru;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name test-demo-sys4tec.ru;

    ssl_certificate /etc/letsencrypt/live/test-demo-sys4tec.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/test-demo-sys4tec.ru/privkey.pem;

    client_max_body_size 100M;

    # API → FastAPI
    location ~ ^/(upload|api|docs|openapi.json) {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Frontend → Next.js
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
```

Активируем конфиг:

```bash
ln -sf /etc/nginx/sites-available/uni-rag /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

### 3. SSL сертификат Let's Encrypt

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d test-demo-sys4tec.ru --non-interactive --agree-tos --email admin@test-demo-sys4tec.ru
```

Сертификат автоматически обновляется каждые 60 дней.

## CI/CD (GitHub Actions)

### Секреты в GitHub

Settings → Secrets and variables → Actions:
- `VPS_HOST` — IP VPS
- `VPS_USER` — root
- `VPS_SSH_KEY` — приватный SSH ключ

### Workflow

`.github/workflows/deploy.yml` при push в main:
1. Подключение к VPS через SSH
2. `git pull origin main`
3. `docker compose down`
4. `docker compose up -d --build`

## Проверка

```bash
# Статус контейнеров
docker compose ps

# Тест загрузки файла
curl -X POST -H "X-API-Key: local-dev-key" -F "file=@test.md" https://test-demo-sys4tec.ru/upload

# Логи
docker compose logs -f api
```

## Полезные команды

```bash
docker compose restart          # Перезапуск сервисов
docker compose up -d --build    # Пересборка
systemctl status nginx          # Статус Nginx
certbot certificates            # Проверка SSL
```




## Стек

FastAPI • Next.js • PostgreSQL (pgvector) • Docker • Nginx • Let's Encrypt • GitHub Actions
