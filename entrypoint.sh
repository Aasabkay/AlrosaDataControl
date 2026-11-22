#!/bin/sh
alembic upgrade head
python -m tools.seed_dictionaries
python -m tools.seed_demo_sources
uvicorn app.main:app --host 0.0.0.0 --proxy-headers --forwarded-allow-ips="*"
