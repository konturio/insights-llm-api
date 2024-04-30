# LLM analytics

### Local run

```shell
cp .env.example .env
```

edit .env

Install virtualenv & requirements

```shell
virtualenv env
. env/bin/activate
pip install -r requirements.txt
```

Run server

```shell
export $(grep -v '^#' .env | xargs -0) 
python3 app/main.py
```

### Docker

Build image

```shell
docker build -t llm-analytics:latest . 
```

Run server

```shell
docker run --rm -it --network=host --env-file .env --name llm-analytics llm-analytics
```

`--network=host` is needed to access local db

### Liveness route

You can use health check to detect if an application is running. It is available via the `/health` route, which responds
with HTTP code 200. 

### check llm-analytics api

get auth token from keycloak and then send the GET request:

```shell
curl -H 'Authorization: Bearer your_long_token' http://127.0.0.1:8000/llm-analytics
```
