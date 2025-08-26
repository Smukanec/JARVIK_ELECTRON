import os
import requests
from dotenv import load_dotenv

API_URL = "https://fura.jarvik-ai.tech"
load_dotenv()
API_KEY = os.getenv("API_KEY")
USERNAME = os.getenv("USERNAME")

if not API_KEY or not USERNAME:
    missing = [name for name, value in (("API_KEY", API_KEY), ("USERNAME", USERNAME)) if not value]
    raise ValueError(f"Missing environment variable(s): {', '.join(missing)}")


def get_context(query):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    data = {"query": query, "user": USERNAME}
    try:
        res = requests.post(
            f"{API_URL}/get_context",
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
