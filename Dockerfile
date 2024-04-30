FROM python:3.11

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY ./app /app

SHELL ["/bin/bash", "-c"]
ENTRYPOINT uvicorn main:create_app --factory --host 0.0.0.0 --port ${PORT} --log-config log-config.yml --log-level $([[ $DEBUG == TRUE ]] && echo "debug" || echo "info")
