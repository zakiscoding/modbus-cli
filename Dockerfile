FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY modbus_cli/ modbus_cli/

RUN pip install --no-cache-dir .

ENTRYPOINT ["modbus"]
