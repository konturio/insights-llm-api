FROM python:3.11

COPY ./requirements.txt /app/requirements.txt

RUN rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY ./app /app
COPY ./tests /tests

SHELL ["/bin/bash", "-c"]
ENTRYPOINT python3 -m app.main
