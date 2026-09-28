FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ bot/

ENV PYTHONUNBUFFERED=1
ENV DB_PATH=/app/data/dailycode.db

CMD ["python", "-m", "bot.main"]
