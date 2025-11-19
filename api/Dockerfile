FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bgp_conflict_api.py .

CMD ["uvicorn", "bgp_conflict_api:app", "--host", "0.0.0.0", "--port", "8001"]

