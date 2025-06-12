# API Endpoints

The service provides the following HTTP routes. All endpoints accept and
return `application/json` unless noted otherwise.

## `POST /llm-analytics`
Generates analytics commentary for a GeoJSON polygon.

**Request body**
```
{
  "appId": "<UUID>",
  "features": <GeoJSON object>
}
```

**Response body**
```
{ "data": "<markdown>" }
```

## `GET /search`
Search for places using Nominatim and return them as a `FeatureCollection`.

Query parameters:
- `appId` – application id.
- `query` – search string.

## `POST /search/click`
Save a user's search choice.

The request contains the same data that `/search` returns plus the selected
feature.

This endpoint is currently unused because the frontend has not been implemented yet.
## `GET /mcda-suggestion`
Returns a multi‑criteria decision analysis (MCDA) configuration.

Query parameters:
- `appId` – application id.
- `query` – free text describing what the user is looking for.

## `GET /health`
Simple liveness probe that returns `200 OK` with `"ok"` in the body.
