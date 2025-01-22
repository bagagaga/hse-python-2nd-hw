FROM python:3.10-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH="${PYTHONPATH}:/app"

CMD ["python", "bot/main.py"]
