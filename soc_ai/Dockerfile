FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY soc_ai ./soc_ai

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["uvicorn", "soc_ai.main:app", "--host", "0.0.0.0", "--port", "8080"]
