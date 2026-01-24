# Uni-RAG: FastAPI + Docling + Next.js

Минималистичный сервис для загрузки документов и извлечения Markdown.
FastAPI принимает файлы и запускает парсинг, Postgres хранит Markdown,
а Next.js дает UI и серверные API для просмотра и удаления документов.

## Что делает сервис

1) Принимает файл через `POST /upload`.
2) Пишет файл на диск чанками и считает SHA-256 от байтов.
3) Если `file_hash` уже есть — сразу возвращает существующий `id`.
4) Если файл новый — ставит задачу в очередь.
5) Docling конвертирует документ в Markdown.
6) Markdown нормализуется, считается `content_hash` и сохраняется в Postgres.
7) Если `content_hash` уже есть — запись не создается.
8) Временный файл удаляется.

## Структура проекта

```
app/
  main.py                     # Инициализация приложения
  core/
    config.py                 # Настройки
  db/
    session.py                # Async engine + миграции
    models.py                 # SQLAlchemy модели
  modules/
    extraction/
      router.py               # /upload
      service.py              # Загрузка + file_hash + очередь
      worker.py               # Docling + content_hash

client/
  app/                         # Страницы + server API
  components/                  # Компоненты UI
  lib/                         # База данных

postgres/
  init/                        # SQL для расширений и FTS
```

## Возможности

- Асинхронная чанковая загрузка
- Очередь в памяти процесса
- Docling + Tesseract OCR (rus+eng)
- Дедуп по `file_hash` и `content_hash`
- Расширения Postgres: vector, pg_trgm, unaccent
- UI на Next.js с превью Markdown и удалением

## OCR (CPU, кириллица)

Используется Tesseract CLI:

- `TesseractCliOcrOptions(lang=["rus", "eng"])`
- `force_full_page_ocr=True` для сканов и изображений
- OCR ограничен 2 потоками CPU
- Гибридный режим для PDF: если есть текстовый слой, OCR не применяется

## Дедупликация

В таблице `documents` хранится два хэша:

- **file_hash**: SHA-256 от байтов файла
  - Проверяется сразу при загрузке.
- **content_hash**: SHA-256 от нормализованного Markdown
  - Проверяется после конвертации.

Нормализация Markdown перед сохранением:

- перевод `\r\n`/`\r` в `\n`
- удаление пробелов в конце строк
- схлопывание 3+ пустых строк до 2
- `strip()` по краям

Важно: content-дедуп происходит после ответа на upload, поэтому новый `id`
может быть выдан, но запись не будет создана при совпадении контента.

## Схема базы

```
documents
  id UUID PRIMARY KEY
  content TEXT NOT NULL
  file_hash TEXT UNIQUE NULL
  content_hash TEXT UNIQUE NULL
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
```

## Конфигурация

Переменные окружения (см. `.env`):

- `API_KEY` — статичный ключ для FastAPI (`X-API-Key`)
- `CORS_ORIGINS` — список разрешенных origin
- `DATABASE_URL` — SQLAlchemy async URL
- `POSTGRES_URL` — доступ к БД для Next.js
- `UPLOAD_DIR` — временная папка
- `MAX_UPLOAD_MB` — лимит размера
- `WORKER_CONCURRENCY` — число воркеров
- `UPLOAD_CHUNK_SIZE` — размер чанка
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `NEXT_PUBLIC_API_URL` — URL FastAPI для браузера
- `NEXT_PUBLIC_API_KEY` — должен совпадать с `API_KEY`

## Docker сервисы

`docker-compose.yml` поднимает:

- `api` (FastAPI + Docling)
- `postgres` (pgvector/pg16)
- `client` (Next.js)

Порты:

- `http://localhost:8000` (FastAPI)
- `http://localhost:3000` (UI)
- `localhost:5432` (Postgres)

## UI

- `/` главная
- `/upload` загрузка файла
- `/documents` список + превью Markdown + удаление

Браузер обращается только к server API Next.js, доступы к БД не видны.

## API

FastAPI:

```
POST /upload
```

Заголовок:

```
X-API-Key: <API_KEY>
```

Server API Next.js:

```
GET /api/documents
GET /api/documents/{id}
DELETE /api/documents/{id}
```

## Запуск

Сборка и запуск:

```
docker compose up --build -d
```

Загрузка через curl:

```
curl -H "X-API-Key: local-dev-key" \
  -F "file=@/path/to/file.pdf" \
  http://localhost:8000/upload
```

UI:

```
http://localhost:3000
```

## Логи и дебаг

Смотреть логи:

```
docker compose logs -f api
```

Ключевые события:

- `extraction: Enqueued ...`
- `worker: Processing ...`
- `worker: Initializing Docling converters`
- `worker: Stored ...`

## Расширения Postgres и FTS

При первом запуске (см. `postgres/init/001_extensions.sql`):

- `vector`
- `pg_trgm`
- `unaccent`
- `default_text_search_config = russian`

Если меняли init‑скрипты и уже есть volume:

```
docker compose down -v
docker compose up --build -d
```

## Ограничения

- content-дедуп работает после ответа на upload.
- OCR качество зависит от сканов и может быть медленным.
- Очередь в памяти не переживает рестарт контейнера.

## Производительность, лимиты и нагрузка

### Базовые лимиты

- Максимальный размер файла: `MAX_UPLOAD_MB` (по умолчанию 100 МБ)
- Размер чанка загрузки: `UPLOAD_CHUNK_SIZE` (по умолчанию 1 МБ)
- Количество воркеров: `WORKER_CONCURRENCY` (по умолчанию 2)
- Потоки OCR: 2 (задано в `worker.py`)

### Поведение под нагрузкой

- Загрузка асинхронная и хорошо масштабируется по клиентам.
- Узкое место — CPU при OCR и парсинге PDF.
- Первые конвертации медленнее из-за прогрева моделей Docling.

### Очередь

- Очередь в памяти процесса (`asyncio.Queue`).
- Если воркеры медленнее, файлы копятся в `UPLOAD_DIR`.
- После рестарта очередь теряется, файлы остаются на диске.

### Память

- OCR модели загружаются один раз и остаются в памяти.
- Большие документы увеличивают пиковое потребление RAM.

### Диск

- Файлы лежат в `UPLOAD_DIR` до завершения обработки.
- В `finally` файл удаляется даже при ошибке.

### Нагрузка на БД

- Вставки одиночные, с уникальными индексами по `file_hash` и `content_hash`.
- Поиск дублей — быстрый (один индексный lookup).
- Большие Markdown увеличивают объем хранения и I/O.

### Рекомендации по настройке

- Увеличивайте `WORKER_CONCURRENCY` только при наличии свободного CPU.
- Увеличивайте `UPLOAD_CHUNK_SIZE` для ускорения записи больших файлов.
- Держите `MAX_UPLOAD_MB` в рамках возможностей диска и RAM.
- Для устойчивой очереди используйте Redis/RabbitMQ.

### Базовые ресурсы (CPU only)

- Легкая нагрузка: 2-4 CPU, 4-8 GB RAM.
- Тяжелые OCR-пакеты: 8+ CPU, 16+ GB RAM.

### Тестирование нагрузки

- Используйте реальные сканы.
- Измеряйте время от upload до записи Markdown.
- Следите за ростом `/tmp/uploads` при стресс-тестах.
