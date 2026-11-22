#!/bin/sh
alembic upgrade head
python -m tools.seed_dictionaries
uvicorn app.main:app --host 0.0.0.0
