# Развёртывание на VPS — alrosadatacontrol.top

Стек: **Postgres 18 + FastAPI (uvicorn) + nginx** (статика фронтенда и прокси на API).
Node на сервере не нужен: `frontend/dist` собран заранее и лежит в репозитории.

Всё, что нужно серверу: Docker + docker compose, открытые порты 80/443.

---

## 1. DNS

В панели регистратора домена `alrosadatacontrol.top` добавить A-записи:

| Тип | Имя | Значение |
|---|---|---|
| A | `@` | `<IP VPS>` |
| A | `www` | `<IP VPS>` |

Проверка (с любого компьютера):

```bash
nslookup alrosadatacontrol.top
```

Должен вернуться IP сервера. DNS может обновляться до 24 часов (обычно 5–15 минут).

---

## 2. Подготовка сервера (Ubuntu/Debian, один раз)

```bash
# Docker + compose plugin
curl -fsSL https://get.docker.com | sh
apt install -y docker-compose-plugin   # если не поставился вместе с Docker
docker --version && docker compose version

# Порты
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp && ufw --force enable
```

---

## 3. Запуск приложения

```bash
git clone https://github.com/Aasabkay/AlrosaDataControl.git alrosa
cd alrosa
```

```bash
cp deploy/.env.example deploy/.env
nano deploy/.env          # ОБЯЗАТЕЛЬНО сменить DB_PASSWORD
```

В `deploy/.env` же задаётся шапка отчёта: `REPORT_ORGANIZATION`, `REPORT_RESPONSIBLE`.

```bash
docker compose -f deploy/docker-compose.prod.yml up -d --build
```

Проверка:

```bash
docker compose -f deploy/docker-compose.prod.yml ps
curl -s http://localhost/health          # {"status":"ok"}
```

Открыть в браузере: `http://alrosadatacontrol.top` (или `http://<IP>` — тоже работает).
Swagger API: `http://alrosadatacontrol.top/docs`.

Миграции Alembic и наполнение справочников выполняет `entrypoint.sh` контейнера `api`
при каждом старте — отдельно ничего запускать не нужно. Там же создаются три
демо-источника, если их ещё нет.

---

## 3.1. Демо-сценарий (проверка, что всё живо)

1. Открыть сайт → «Загрузка». В списке источников уже есть «Бухгалтерия (XLSX)»,
   «Выгрузка CMDB (CSV)», «Акт инвентаризации (CSV)».
2. Загрузить три файла из `sample_data/demo/`:

   | Файл | Источник |
   |---|---|
   | `source_1_buh.xlsx` | Бухгалтерия (XLSX) |
   | `source_2_cmdb.csv` | Выгрузка CMDB (CSV) |
   | `source_3_act.csv` | Акт инвентаризации (CSV) |

3. В блоке «Запуск сверки» нажать **«Запустить сверку»** — сверяются последние
   загрузки по каждому источнику.
4. «Дашборд»: **20 активов, 17 замечаний**, разбивка по кодам.
   «Отчёт» → «Скачать XLSX».

Те же числа зафиксированы в `sample_data/demo/expected.json` — это доказательство,
что система находит ровно засеянные ошибки.

---

## 4. HTTPS (Let's Encrypt)

nginx уже отдаёт `/.well-known/acme-challenge/` из `deploy/certbot/www`,
поэтому сертификат выпускается без остановки сайта.

```bash
# из корня репозитория (папка alrosa)
mkdir -p deploy/certbot/www deploy/certbot/conf

docker run --rm \
  -v "$PWD/deploy/certbot/conf:/etc/letsencrypt" \
  -v "$PWD/deploy/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --webroot -w /var/www/certbot \
  -d alrosadatacontrol.top -d www.alrosadatacontrol.top \
  --email <ваша почта> --agree-tos --no-eff-email
```

Затем в `deploy/nginx.conf` **раскомментировать блок `server { listen 443 ssl; ... }`**
(он в конце файла) и перезапустить nginx:

```bash
docker compose -f deploy/docker-compose.prod.yml restart nginx
```

Проверка: `https://alrosadatacontrol.top`.

Продление (сертификат на 90 дней) — добавить в `crontab -e`:

```
0 3 * * * cd /root/alrosa && docker run --rm -v "$PWD/deploy/certbot/conf:/etc/letsencrypt" -v "$PWD/deploy/certbot/www:/var/www/certbot" certbot/certbot renew --webroot -w /var/www/certbot --quiet && docker compose -f deploy/docker-compose.prod.yml exec -T nginx nginx -s reload
```

---

## 5. Обновление версии

```bash
cd alrosa
git pull
docker compose -f deploy/docker-compose.prod.yml up -d --build
```

`frontend/dist` обновляется вместе с `git pull` — nginx подхватывает новую статику сразу.

---

## 6. Эксплуатация

```bash
# логи
docker compose -f deploy/docker-compose.prod.yml logs -f api
docker compose -f deploy/docker-compose.prod.yml logs -f nginx

# перезапуск
docker compose -f deploy/docker-compose.prod.yml restart api

# бэкап базы
docker compose -f deploy/docker-compose.prod.yml exec -T db \
  pg_dump -U alrosa_user alrosa_assets > backup_$(date +%F).sql
```

Данные лежат в docker-томах `deploy_pgdata` и `deploy_uploads-data`
(имена с префиксом проекта). `docker compose down` их не удаляет;
`down -v` — **удаляет**, использовать осторожно.

---

## 7. Если что-то не работает

| Симптом | Что проверить |
|---|---|
| `502 Bad Gateway` на сайте | `docker compose ... ps` — контейнер `api` жив? `logs api` |
| Сайт открывается по IP, но не по домену | DNS ещё не обновился / A-запись неверная (`nslookup`) |
| `502` и в логах api `connection refused` к db | не совпал пароль: `DB_PASSWORD` в `deploy/.env`; после смены — `down` и `up` (том с прежним паролем) |
| Ошибка `password authentication failed` после смены пароля | старый том хранит старый пароль: `docker compose ... down -v` (данные пропадут) или `ALTER USER` в psql |
| Certbot: `Timeout during connect` | порт 80 закрыт фаерволом / DNS ещё не указывает на сервер |
| Пустая страница, в консоли 404 на `/assets/...` | не закоммичен `frontend/dist` — на сервере сделать `git pull` |
