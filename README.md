# LLM analytics

API and database schema are documented in the [docs](docs/) directory.

### Local run

```shell
cp .env.example .env
```

edit .env

Install dependencies using Poetry. Poetry will create a dedicated virtual
environment for the project when installing packages.

```shell
pip install poetry
poetry install
`poetry env activate`
```

Run server from within the Poetry shell

```shell
set -a; . <(grep -v '^#' .env | grep -v '^$' | sed -e "s/=/='/" -e "s/$/'/")
python3 -m app.main
```

Run tests from the Poetry shell

```shell
python tests/test_analytics.py
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

get auth token from keycloak and then do POST:

```shell
curl http://localhost:8000/llm-analytics \
  -H 'Authorization: Bearer your_long_auth_token' \
  -H 'Content-Type: application/json' \
  -d '{
    "appId": "9043acf9-2cf3-48ac-9656-a5d7c4b7593d",
    "features": {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [-77.034084142948, 38.909671288923],
            [-77.034084142948, 38.919671288923],
            [-77.014084142948, 38.919671288923],
            [-77.014084142948, 38.909671288923],
            [-77.034084142948, 38.909671288923]
          ]
        ]
      },
      "properties": {
        "name": "Area name"
      }
    }
  }'
```

also works with FeatureCollection:

```shell
curl http://localhost:8000/llm-analytics \
    -H 'Authorization: Bearer your_long_auth_token' \
  -H 'Content-Type: application/json' \
  -d '{
    "appId": "9043acf9-2cf3-48ac-9656-a5d7c4b7593d",
    "features": {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "properties": {},
          "geometry": {
            "type": "Polygon",
            "coordinates": [
              [
                [-77.034084142948, 38.909671288923],
                [-77.034084142948, 38.919671288923],
                [-77.014084142948, 38.919671288923],
                [-77.014084142948, 38.909671288923],
                [-77.034084142948, 38.909671288923]
              ]
            ]
          }
        }
      ]
    }
  }'
```
