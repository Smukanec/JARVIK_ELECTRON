from flask import Flask, request, jsonify
import subprocess
import threading
import webbrowser
import json
import requests
import logging
import unicodedata
from fura_client import get_context

app = Flask(__name__, static_folder="static", static_url_path="")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_models():
    logger.info("Attempting to fetch models using 'ollama list'")
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
            except json.JSONDecodeError as e:
                logger.warning("Failed to decode line as JSON: %s", e)
                continue
        logger.info("Models obtained via subprocess: %s", models)
        return models
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error("Error running 'ollama list': %s", e)
        try:
            logger.info("Falling back to HTTP API for model list")
            resp = requests.get("http://localhost:11434/api/tags", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            models = [m.get("name") for m in data.get("models", [])]
            logger.info("Models obtained via HTTP API: %s", models)
            return models
        except requests.RequestException as e:
            logger.error("HTTP error while fetching models: %s", e)
            return []


def strip_diacritics(text):
    """Return text without diacritics for internal comparisons."""
    if not isinstance(text, str):
        return text
    return (
        unicodedata.normalize("NFD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
    )


def choose_model(prompt):
    prompt = strip_diacritics(prompt or "").lower()
    if "program" in prompt or "kod" in prompt:
        return "phi3"
    elif "pravo" in prompt or "smlouva" in prompt:
        return "llama3"
    else:
        return "mistral"

@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/simple")
def simple():
    """Serve a minimal UI for troubleshooting encoding issues."""
    return app.send_static_file("simple.html")


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
    memory = data.get("memory", "private")

    logger.info("Received ask request for model %s", requested_model)

    if not api_key or not username:
        logger.error("Missing API key or username")
        return jsonify({"error": "Missing api_key or username"}), 400
    if not query:
        logger.error("No message provided in request")
        return jsonify({"error": "No message provided"}), 400

    if api_url:
        context_data = get_context(query, api_key, username, api_url, memory)
    else:
        context_data = get_context(query, api_key, username, memory=memory)

    if "error" in context_data:
        logger.error("Context retrieval failed: %s", context_data.get("error"))
        return jsonify(context_data), 401

    available_models = fetch_models()
    if not available_models:
        logger.error("No models available")
        return jsonify({"error": "No models available"}), 503

    if requested_model and requested_model in available_models:
        model = requested_model
    else:
        model = choose_model(query)
        if model not in available_models:
            model = available_models[0]
    context_text = context_data.get("context", "")
    debug_data = context_data.get("debug")
    full_prompt = context_text + "\n" + query
    logger.info("Using model %s", model)

    try:
        response = subprocess.run(
            ["ollama", "run", model],
            input=full_prompt,
            capture_output=True,
            check=True,
            text=True,
            timeout=60,
        )
        logger.info("Model %s responded successfully", model)
        return jsonify(
            {
                "response": response.stdout,
                "context": context_text,
                "debug": debug_data,
            }
        )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or str(e)
        logger.error("Subprocess failed: %s", error_msg)
        return jsonify({"error": f"Subprocess failed: {error_msg}"}), 500
    except subprocess.TimeoutExpired as e:
        logger.error("Subprocess timed out: %s", e)
        return jsonify({"error": "Subprocess timed out"}), 500
    except FileNotFoundError as e:
        logger.error("Ollama executable not found: %s", e)
        return jsonify({"error": "Ollama executable not found"}), 500


@app.route("/code", methods=["POST"])
def code():
    data = request.get_json() or {}

    source_code = data.get("code")
    instruction = data.get("instruction")
    files = data.get("files") or {}
    api_key = data.get("api_key")
    username = data.get("username")
    api_url = data.get("api_url")
    requested_model = data.get("model")
    memory = data.get("memory", "private")

    logger.info("Received code request for model %s", requested_model)

    if not api_key or not username:
        logger.error("Missing API key or username")
        return jsonify({"error": "Missing api_key or username"}), 400
    if not source_code or not instruction:
        logger.error("Missing code or instruction")
        return jsonify({"error": "Missing code or instruction"}), 400

    if api_url:
        context_data = get_context(instruction, api_key, username, api_url, memory)
    else:
        context_data = get_context(instruction, api_key, username, memory=memory)

    if "error" in context_data:
        logger.error("Context retrieval failed: %s", context_data.get("error"))
        return jsonify(context_data), 401

    available_models = fetch_models()
    if not available_models:
        logger.error("No models available")
        return jsonify({"error": "No models available"}), 503

    if requested_model and requested_model in available_models:
        model = requested_model
    else:
        model = choose_model(instruction)
        if model not in available_models:
            model = available_models[0]

    context_text = context_data.get("context", "")
    debug_data = context_data.get("debug")
    files_text = ""
    for name, content in files.items():
        files_text += f"\nFilename: {name}\n{content}\n"

    full_prompt = (
        context_text
        + "\nInstruction: "
        + instruction
        + "\n\nCode:\n"
        + source_code
        + files_text
    )
    logger.info("Using model %s for code endpoint", model)

    try:
        response = subprocess.run(
            ["ollama", "run", model],
            input=full_prompt,
            capture_output=True,
            check=True,
            text=True,
            timeout=60,
        )
        logger.info("Model %s responded successfully", model)
        return jsonify(
            {
                "response": response.stdout,
                "context": context_text,
                "debug": debug_data,
            }
        )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or str(e)
        logger.error("Subprocess failed: %s", error_msg)
        return jsonify({"error": f"Subprocess failed: {error_msg}"}), 500
    except subprocess.TimeoutExpired as e:
        logger.error("Subprocess timed out: %s", e)
        return jsonify({"error": "Subprocess timed out"}), 500
    except FileNotFoundError as e:
        logger.error("Ollama executable not found: %s", e)
        return jsonify({"error": "Ollama executable not found"}), 500

if __name__ == "__main__":
    threading.Timer(1.0, lambda: webbrowser.open("http://localhost:8000")).start()
    app.run(port=8000)
