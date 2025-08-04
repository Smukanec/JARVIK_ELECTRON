import requests
import os

API_URL = "https://fura.jarvik-ai.tech"
API_KEY = os.getenv("API_KEY")
USERNAME = os.getenv("USERNAME")

def get_context(query):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    data = {"query": query, "user": USERNAME}
    res = requests.post(f"{API_URL}/get_context", json=data, headers=headers)
    return res.json()