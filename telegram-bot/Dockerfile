FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY bot ./bot

RUN pip install --no-cache-dir -e .

EXPOSE 8081

CMD ["uvicorn", "bot.main:app", "--host", "0.0.0.0", "--port", "8081"]
