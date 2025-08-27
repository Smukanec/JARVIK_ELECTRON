from flask import Flask, request, jsonify
import subprocess
import threading
import webbrowser
from fura_client import get_context
from model_router import choose_model

app = Flask(__name__, static_folder="static", static_url_path="")

@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/models")
def models():
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=True,
        )
        lines = result.stdout.strip().splitlines()
        models = [line.split()[0] for line in lines[1:]] if lines else []
        return jsonify({"models": models})
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or str(e)
        return jsonify({"models": [], "error": f"Subprocess failed: {error_msg}"}), 500
    except Exception as e:
        return jsonify({"models": [], "error": str(e)}), 500

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json() or {}

    query = data.get("message")
    api_key = data.get("api_key")
    username = data.get("username")
    api_url = data.get("api_url")

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

    model = data.get("model") or choose_model(query)
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
