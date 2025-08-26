import requests

API_URL = "https://fura.jarvik-ai.tech"


def get_context(query, api_key, username, api_url: str = API_URL):
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {"query": query, "user": username}
    try:
        res = requests.post(
            f"{api_url}/get_context",
            json=data,
            headers=headers,
            timeout=10,
        )
        res.raise_for_status()
    except requests.RequestException as exc:
        return {"error": "API request failed", "details": str(exc)}

    try:
        return res.json()
    except ValueError:
        return {"error": "Invalid JSON response", "details": res.text}
