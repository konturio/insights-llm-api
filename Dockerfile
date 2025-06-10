FROM python:3.11

WORKDIR /app

RUN pip install poetry
COPY ./pyproject.toml /app/
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

COPY ./app /app/app
COPY ./tests /app/tests

SHELL ["/bin/bash", "-c"]
ENTRYPOINT ["python3", "-m", "app.main"]
