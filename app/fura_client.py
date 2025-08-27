import json
import os
import time

import requests

API_URL = "https://fura.jarvik-ai.tech"
CACHE_FILE = os.path.join(os.path.dirname(__file__), "context_cache.json")
CACHE_TTL = 60 * 60 * 24  # 24 hours


def _load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except json.JSONDecodeError:
            return {}
    return {}


def _save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as fh:
            json.dump(cache, fh)
    except OSError:
        pass


def get_context(query, api_key, username, api_url: str = API_URL, memory: str = "private"):
    cache = _load_cache()
    now = time.time()
    cached = cache.get(query)
    if cached and now - cached.get("timestamp", 0) < CACHE_TTL:
        cached_data = cached.get("data")
    else:
        cached_data = None

    headers = {"Authorization": f"Bearer {api_key}"}
    data = {"query": query, "user": username, "public": memory == "public"}
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
        _save_cache(cache)
        return result
    except requests.RequestException as exc:
        if cached_data is not None:
            return cached_data
        return {"error": "API request failed", "details": str(exc)}
    except ValueError:
        return {"error": "Invalid JSON response", "details": res.text}
