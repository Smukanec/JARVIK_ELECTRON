from flask import Flask, request, jsonify
import subprocess
import threading
import webbrowser
import json
import requests
from fura_client import get_context

app = Flask(__name__, static_folder="static", static_url_path="")


def fetch_models():
    try:
        result = subprocess.run(
            ["ollama", "list", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )

        models = []
        for line in result.stdout.splitlines():
            try:
                obj = json.loads(line)
                name = obj.get("name")
                if name:
                    models.append(name)
            except json.JSONDecodeError:
                continue
        return models
    except Exception:
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            return [m.get("name") for m in data.get("models", [])]
        except Exception:
            return []


def choose_model(prompt):
    prompt = (prompt or "").lower()
    if "program" in prompt or "kód" in prompt:
        return "phi3"
    elif "právo" in prompt or "smlouva" in prompt:
        return "llama3"
    else:
        return "mistral"

@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/models", methods=["GET"])
def models():
    return jsonify(fetch_models())

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json() or {}

    query = data.get("message")
    api_key = data.get("api_key")
    username = data.get("username")
    api_url = data.get("api_url")
    requested_model = data.get("model")

    if not api_key or not username:
        return jsonify({"error": "Missing api_key or username"}), 400
    if not query:
        return jsonify({"error": "No message provided"}), 400

    if api_url:
        context_data = get_context(query, api_key, username, api_url)
    else:
        context_data = get_context(query, api_key, username)

    if "error" in context_data:
        return jsonify(context_data), 401

    available_models = fetch_models()
    if not available_models:
        return jsonify({"error": "No models available"}), 503

    if requested_model and requested_model in available_models:
        model = requested_model
    else:
        model = choose_model(query)
        if model not in available_models:
            model = available_models[0]
    full_prompt = context_data.get("context", "") + "\n" + query

    try:
        response = subprocess.run(
            ["ollama", "run", model],
            input=full_prompt,
            capture_output=True,
            check=True,
            text=True,
            timeout=60,
        )
        return jsonify({"response": response.stdout})
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or str(e)
        return jsonify({"error": f"Subprocess failed: {error_msg}"}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Subprocess timed out"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    threading.Timer(1.0, lambda: webbrowser.open("http://localhost:8000")).start()
    app.run(port=8000)
