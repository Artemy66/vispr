# mysite

Простое веб-приложение (визитка) с редактированием, формой заявок,
health-check и метриками Prometheus. Разворачивается в Docker,
собирается в CI/CD, мониторится через Prometheus + Grafana + cAdvisor.

## Быстрый старт (локально)

    cp .env.example .env
    # отредактируйте .env (пароль админки, секрет)
    docker compose up -d --build

Открыть:
- Сайт:            http://localhost:8000/
- Админка:         http://localhost:8000/admin  (пароль из ADMIN_PASSWORD)
- Метрики:         http://localhost:8000/metrics
- Health:          http://localhost:8000/health
- Prometheus:      http://localhost:9090
- Grafana:         http://localhost:3000        (admin / GRAFANA_PASSWORD)
- cAdvisor:        http://localhost:8080

## Остановить

    docker compose down

## Данные

SQLite хранится в ./data/app.db — переживает пересоздание контейнера.

## CI/CD

При push в `main` GitHub Actions:
1. Собирает wheel (артефакт).
2. Собирает и пушит Docker-образ в GHCR с тегом = commit SHA.
3. По SSH заходит на сервер и запускает `deploy.sh`.

Требуются Secrets: SSH_HOST, SSH_USER, SSH_KEY (и SSH_PORT при необходимости).

## Метрики

- `site_visits_total{path}` — посещения по путям.
- `site_leads_total` — отправленные заявки.
- `site_admin_edits_total` — сохранения в админке.
- `site_uptime_seconds` — аптайм.

### «Посещений в час» (Grafana/PromQL)

    sum(rate(site_visits_total[1h])) * 3600

### CPU контейнера приложения

    rate(container_cpu_usage_seconds_total{name="mysite-app"}[5m])

### RAM контейнера приложения

    container_memory_usage_bytes{name="mysite-app"}

## Структура

    app.py                 — Flask: роуты, БД, метрики, health
    templates/             — HTML (Jinja2)
    static/css/            — CSS
    Dockerfile             — сборка образа
    docker-compose.yml     — app + Prometheus + Grafana + cAdvisor
    prometheus.yml         — конфиг сбора метрик
    deploy.sh              — скрипт деплоя на сервере
    .github/workflows/     — CI/CD

## Настройка Grafana

1. Войти: admin / GRAFANA_PASSWORD.
2. Connections → Data sources → Prometheus → URL `http://prometheus:9090`.
3. Создать dashboard, добавить панели с PromQL-запросами выше.