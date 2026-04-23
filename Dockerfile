FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN mkdir -p /app/data
RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["aiops", "api", "--host", "0.0.0.0", "--port", "8080"]
