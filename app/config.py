import os
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")
DB_URL = os.getenv("DB_URL")
UPLOAD_DIR = os.getenv("UPLOAD_DIR")

# Шапка отчёта. Задаётся на сервере через окружение, чтобы отчёт выглядел
# как документ организации, а не как выгрузка из прототипа.
REPORT_ORGANIZATION = os.getenv("REPORT_ORGANIZATION", "")
REPORT_RESPONSIBLE = os.getenv("REPORT_RESPONSIBLE", "")