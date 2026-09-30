# Prediction Agent Lab

Минимальный агент на VPS для воспроизводимых экспериментов с prediction-сервисами.
Рабочий demo → очередь → worker → результат; необязательные платный HTTP-адаптер,
AI-анализ через OpenAI-совместимый API и Telegram. Без автоматических покупок и ставок.
Это самостоятельный каркас, не установка Hermes.

## Архитектура

- **FastAPI**: защищённый API и простой HTML/JS dashboard.
- **Worker**: забирает задания атомарно из SQLite, вызывает провайдер, сохраняет результат.
- **SQLite WAL**: очередь и последние результаты в постоянном Docker volume.
- **Telegram**: long polling, только личные чаты и разрешённые user IDs.
- **Docker Compose**: один образ, отдельные процессы API/worker/bot.
- **CI**: Ruff, pytest, проверка Compose и сборка контейнера.

```text
src/prediction_agent/     API, worker, adapters, Telegram, dashboard
experiments/             JSON-спецификации и методика сравнения
 tests/                  сквозные и контрактные проверки
.github/workflows/       CI
.env.example             шаблон конфигурации, без секретов
Dockerfile               непривилегированный контейнер
 docker-compose.yml      сервисы и постоянное хранилище
```

## Запуск на Ubuntu VPS

Установите Git, Docker Engine и Compose plugin по официальной документации Docker.

```bash
git clone https://github.com/ab-dgtl/Codex1.git
cd Codex1
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Вставьте сгенерированный токен в APP_TOKEN в .env
chmod 600 .env
docker compose up -d --build
```

Dashboard: http://localhost:8000. На своём компьютере откройте SSH-туннель:

```bash
ssh -L 8000:127.0.0.1:8000 USER@VPS
```

Введите APP_TOKEN в dashboard, запустите Demo и нажмите Refresh через несколько секунд.
Токен хранится только в памяти страницы. API слушает loopback хоста;
для публичного доступа сначала настройте HTTPS reverse proxy и ограничение доступа.

```bash
# APP_TOKEN должен быть определён в окружении текущего shell
curl -H "Authorization: Bearer $APP_TOKEN" -H 'Content-Type: application/json' \
  --data @experiments/demo.json http://localhost:8000/api/runs
curl -H "Authorization: Bearer $APP_TOKEN" http://localhost:8000/api/runs

docker compose logs --tail=100 worker
docker compose down # volume сохраняется; down -v удаляет результаты
```

## Telegram

Создайте бота через BotFather, задайте TELEGRAM_BOT_TOKEN и
TELEGRAM_ALLOWED_USER_IDS (числовые Telegram user IDs через запятую).

```bash
docker compose --profile telegram up -d --build
```

В личном чате: `/start`, `/run <вопрос>`, `/runs`. Команда `/run` использует
только бесплатный demo. Платные эксперименты запускаются через API/dashboard.
Не запускайте второй polling-процесс для этого же бота.

## Платные сервисы и AI

HTTP-адаптер — контракт для интеграции, а не готовый коннектор конкретного сервиса:

- задайте PROVIDER_URL, PROVIDER_ALLOWED_HOSTS (точные hostname через запятую), PROVIDER_API_KEY;
- запрос: HTTPS POST, Bearer token, JSON `{"question":"..."}`;
- ответ: `{"probability":0.7,"rationale":"..."}`;
- в эксперименте установите `"provider":"http"`.

Для другого API реализуйте адаптер в providers.py. Используйте официальные API
или разрешённые сервисом способы доступа. Host allowlist — не полноценная защита
от SSRF: конфигурацию меняет только администратор; для недоверенных конфигураций
нужен egress firewall. Редиректы и автоматические повторы платных запросов отключены.

AI-анализ: задайте LLM_API_KEY, LLM_MODEL, при необходимости LLM_URL;
установите `"analyze":true`. Прогноз будет отправлен выбранному AI-провайдеру.
Анализ оценивает аргументацию; не проверяет будущий исход. Он может стоить денег.
Жёсткого денежного лимита здесь пока нет — настройте лимиты у провайдеров.

## Секреты и хранение

.env исключён из Git и Docker build context. Не коммитьте ключи, сессии браузера
или приватные ответы сервисов. APP_TOKEN обязателен (минимум 24 символа).
Все данные экспериментов доступны владельцам токена и разрешённым Telegram-пользователям.
Runtime-секреты передаются через окружение: это стартовый вариант, не secret manager.
CI не требует секретов. База в agent-data не шифруется; резервируйте volume на VPS.
Для согласованного backup остановите сервисы перед копированием SQLite/WAL-файлов.

## Разработка и проверки

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
ruff check .
pytest -q
# Для локального API/worker: APP_TOKEN задан, DATABASE_PATH=data/agent.db
uvicorn prediction_agent.api:app --reload
# Во втором terminal:
python -m prediction_agent.worker
```

## Границы стартовой версии

Demo — фиксированная синтетическая вероятность 0.5, без реального прогноза.
HTTP-интеграция требует адаптации к выбранному сервису; браузерного worker пока нет.
Нет автопланировщика, биллинга, rate limit, разрешения исходов и оценки качества.
При аварии worker задание остаётся running: проверьте логи и статус запроса у
провайдера, затем создайте новый эксперимент вручную. Автоповтор мог бы повторно
списать деньги. Одно задание не повторяется автоматически; база предназначена
для одного VPS, не распределённых workers. API показывает последние 100 запусков.

Следующее развитие: service-specific adapters, исходы и Brier score/calibration,
учёт затрат, экспорт результатов, лимиты, затем отдельный браузерный worker.
