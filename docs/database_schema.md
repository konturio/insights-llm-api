# Database Schema

The service uses a PostgreSQL database. The relevant tables are:

## `llm_cache`
Stores generated LLM responses to avoid repeated calls.

| Column       | Type    | Notes                       |
|--------------|---------|-----------------------------|
| `hash`       | text    | MD5 hash of the request     |
| `request`    | text    | Original request parameters |
| `response`   | text    | LLM response text           |
| `model_name` | text    | OpenAI model used           |

```
PRIMARY KEY (hash, model_name)
```

## `nominatim_cache`
Caches responses from the Nominatim search API.

| Column        | Type  | Notes                |
|---------------|-------|----------------------|
| `query_hash`  | text  | MD5 of the request   |
| `query`       | text  | Request URL          |
| `response`    | jsonb | Cached API response  |

```
PRIMARY KEY (query_hash)
```

## `search_history`
Tracks what users clicked in the search results.

| Column                | Type  | Notes                 |
|-----------------------|-------|-----------------------|
| `app_id`              | uuid  | Client application ID |
| `query`               | text  | Search query          |
| `search_results`      | jsonb | Result set            |
| `selected_feature`    | jsonb | Chosen location       |
| `selected_feature_type` | text | Type of the feature   |

