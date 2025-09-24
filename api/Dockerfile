FROM python:3.11-slim

RUN apt-get update && apt-get install -y curl net-tools

COPY requirements.txt /api/requirements.txt
RUN pip install --no-cache-dir -r /api/requirements.txt

COPY . /api

WORKDIR /

CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "3000"]
