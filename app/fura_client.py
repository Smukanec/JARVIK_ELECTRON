import os
import time
import shelve

import requests

API_URL = "https://fura.jarvik-ai.tech"
CACHE_FILE = os.path.join(os.path.dirname(__file__), "context_cache.db")
CACHE_TTL = 60 * 60 * 24  # 24 hours
CACHE_MAX_ITEMS = 128


def _open_cache():
    return shelve.open(CACHE_FILE)


def _prune_cache(cache):
    """Remove oldest items from cache when exceeding max items."""
    excess = len(cache) - CACHE_MAX_ITEMS
    if excess <= 0:
        return
    sorted_items = sorted(cache.items(), key=lambda item: item[1].get("timestamp", 0))
    for key, _ in sorted_items[:excess]:
        del cache[key]


def get_context(query, api_key, username, api_url: str = API_URL, remember: bool = False):
    now = time.time()
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {"query": query, "user": username, "remember": remember}

    with _open_cache() as cache:
        cached = cache.get(query)
        if cached and now - cached.get("timestamp", 0) < CACHE_TTL:
            cached_data = cached.get("data")
        else:
            cached_data = None

        try:
            res = requests.post(
                f"{api_url}/get_context",
                json=data,
                headers=headers,
                timeout=10,
            )
            res.raise_for_status()
            result = res.json()
            cache[query] = {"timestamp": now, "data": result}
            _prune_cache(cache)
            cache.sync()
            return result
        except requests.RequestException as exc:
            if cached_data is not None:
                return cached_data
            return {"error": "API request failed", "details": str(exc)}
        except ValueError:
            return {"error": "Invalid JSON response", "details": res.text}

