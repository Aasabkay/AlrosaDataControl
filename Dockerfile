FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/uploads && chmod +x entrypoint.sh

ENTRYPOINT ["sh", "./entrypoint.sh"]
