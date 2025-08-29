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
        proc = subprocess.Popen(
            ["ollama", "list", "--json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        models = []
        for line in proc.stdout:
            try:
                obj = json.loads(line)
                name = obj.get("name")
                if name:
                    models.append(name)
            except json.JSONDecodeError as e:
                logger.warning("Failed to decode line as JSON: %s", e)
                continue
        proc.stdout.close()
        stderr = proc.stderr.read()
        returncode = proc.wait()
        if returncode != 0:
            raise subprocess.CalledProcessError(
                returncode, proc.args, stderr=stderr
            )
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


@app.route("/auth/me", methods=["POST"])
def auth_me():
    data = request.get_json() or {}
    api_url = data.get("api_url")
    username = data.get("username")
    api_key = data.get("api_key")

    if not api_url or not username or not api_key:
        return jsonify({"error": "Missing api_url, username or api_key"}), 400

    headers = {"Authorization": f"Bearer {api_key}"}
    params = {"user": username}

    try:
        res = requests.get(f"{api_url}/auth/me", headers=headers, params=params, timeout=10)
        if res.ok:
            return jsonify(res.json())
        return jsonify(res.json()), res.status_code
    except requests.RequestException as exc:
        logger.error("Auth check failed: %s", exc)
        return jsonify({"error": "Auth check failed", "details": str(exc)}), 502

def _validate_fura_fields(message, api_url, username, api_key):
    """Ensure required fields for the Fura request are non-empty strings."""
    errors = {}
    if not isinstance(message, str) or not message.strip():
        errors["message"] = "message must be a non-empty string"
    if not isinstance(api_url, str) or not api_url.strip():
        errors["api_url"] = "api_url must be a non-empty string"
    if not isinstance(username, str) or not username.strip():
        errors["username"] = "username must be a non-empty string"
    if not isinstance(api_key, str) or not api_key.strip():
        errors["api_key"] = "api_key must be a non-empty string"
    return errors

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json() or {}
    message = data.get("message")
    api_url = data.get("api_url")
    username = data.get("username")
    api_key = data.get("api_key")
    requested_model = data.get("model")
    remember = data.get("remember", False)

    errors = _validate_fura_fields(message, api_url, username, api_key)
    if errors:
        logger.error("Validation errors: %s", errors)
        return (
            jsonify(
                {
                    "errors": errors,
                    "error_code": 400,
                    "context_used": False,
                    "context_items_count": 0,
                    "memory_mode": "public" if remember else "private",
                }
            ),
            400,
        )

    query = message
    logger.info("Received ask request for model %s", requested_model)

    context_data = get_context(query, api_key, username, api_url, remember)

    if "error" in context_data:
        logger.error("Context retrieval failed: %s", context_data.get("error"))
        context_data.update(
            {
                "error_code": 401,
                "context_used": False,
                "context_items_count": 0,
                "memory_mode": "public" if remember else "private",
            }
        )
        return jsonify(context_data), 401

    available_models = fetch_models()
    if not available_models:
        logger.error("No models available")
        return (
            jsonify(
                {
                    "error": "No models available",
                    "error_code": 503,
                    "context_used": False,
                    "context_items_count": 0,
                    "memory_mode": "public" if remember else "private",
                }
            ),
            503,
        )

    if requested_model and requested_model in available_models:
        model = requested_model
    else:
        model = choose_model(query)
        if model not in available_models:
            model = available_models[0]
    context_text = context_data.get("context", "")
    debug_data = context_data.get("debug")
    context_used = bool(context_text.strip())
    if isinstance(debug_data, dict):
        context_items_count = len(debug_data.get("items", []))
    else:
        context_items_count = 0
    full_prompt = context_text + "\n" + query
    logger.info("Using model %s", model)

    try:
        proc = subprocess.Popen(
            ["ollama", "run", model],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        proc.stdin.write(full_prompt)
        proc.stdin.close()
        output_lines = []
        for line in proc.stdout:
            output_lines.append(line)
        proc.stdout.close()
        stderr = proc.stderr.read()
        try:
            returncode = proc.wait(timeout=60)
        except subprocess.TimeoutExpired as e:
            proc.kill()
            logger.error("Subprocess timed out: %s", e)
            return (
                jsonify(
                    {
                        "error": "Subprocess timed out",
                        "error_code": 504,
                        "context_used": context_used,
                        "context_items_count": context_items_count,
                        "memory_mode": "public" if remember else "private",
                    }
                ),
                500,
            )
        output_text = "".join(output_lines)
        if returncode != 0:
            raise subprocess.CalledProcessError(
                returncode, proc.args, output=output_text, stderr=stderr
            )
        logger.info("Model %s responded successfully", model)
        return jsonify(
            {
                "response": output_text,
                "context": context_text,
                "debug": debug_data,
                "context_used": context_used,
                "context_items_count": context_items_count,
                "memory_mode": "public" if remember else "private",
                "error_code": 0,
            }
        )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or str(e)
        logger.error("Subprocess failed: %s", error_msg)
        return (
            jsonify(
                {
                    "error": f"Subprocess failed: {error_msg}",
                    "error_code": 500,
                    "context_used": context_used,
                    "context_items_count": context_items_count,
                    "memory_mode": "public" if remember else "private",
                }
            ),
            500,
        )
    except FileNotFoundError as e:
        logger.error("Ollama executable not found: %s", e)
        return (
            jsonify(
                {
                    "error": "Ollama executable not found",
                    "error_code": 500,
                    "context_used": context_used,
                    "context_items_count": context_items_count,
                    "memory_mode": "public" if remember else "private",
                }
            ),
            500,
        )


@app.route("/knowledge", methods=["POST"])
def knowledge():
    data = request.get_json() or {}
    query = data.get("query")
    api_url = data.get("api_url")
    username = data.get("username")
    api_key = data.get("api_key")
    if not all([query, api_url, username, api_key]):
        return jsonify({"error": "Missing required fields"}), 400
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"query": query, "user": username}
    try:
        res = requests.post(
            f"{api_url}/knowledge/search",
            json=payload,
            headers=headers,
            timeout=10,
        )
        res.raise_for_status()
        return jsonify(res.json())
    except requests.RequestException as exc:
        logger.error("Knowledge search failed: %s", exc)
        return jsonify({"error": "Knowledge search failed", "details": str(exc)}), 500


@app.route("/crawl", methods=["POST"])
def crawl():
    data = request.get_json() or {}
    url = data.get("url")
    api_url = data.get("api_url")
    username = data.get("username")
    api_key = data.get("api_key")
    if not all([url, api_url, username, api_key]):
        return jsonify({"error": "Missing required fields"}), 400
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"url": url, "user": username}
    try:
        res = requests.post(
            f"{api_url}/crawl",
            json=payload,
            headers=headers,
            timeout=10,
        )
        res.raise_for_status()
        return jsonify(res.json())
    except requests.RequestException as exc:
        logger.error("Crawl failed: %s", exc)
        return jsonify({"error": "Crawl failed", "details": str(exc)}), 500


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
    remember = data.get("remember", False)

    logger.info("Received code request for model %s", requested_model)

    if not api_key or not username:
        logger.error("Missing API key or username")
        return (
            jsonify(
                {
                    "error": "Missing api_key or username",
                    "error_code": 400,
                    "context_used": False,
                    "context_items_count": 0,
                    "memory_mode": "public" if remember else "private",
                }
            ),
            400,
        )
    if not source_code or not instruction:
        logger.error("Missing code or instruction")
        return (
            jsonify(
                {
                    "error": "Missing code or instruction",
                    "error_code": 400,
                    "context_used": False,
                    "context_items_count": 0,
                    "memory_mode": "public" if remember else "private",
                }
            ),
            400,
        )

    if api_url:
        context_data = get_context(instruction, api_key, username, api_url, remember)
    else:
        context_data = get_context(instruction, api_key, username, remember=remember)

    if "error" in context_data:
        logger.error("Context retrieval failed: %s", context_data.get("error"))
        context_data.update(
            {
                "error_code": 401,
                "context_used": False,
                "context_items_count": 0,
                "memory_mode": "public" if remember else "private",
            }
        )
        return jsonify(context_data), 401

    available_models = fetch_models()
    if not available_models:
        logger.error("No models available")
        return (
            jsonify(
                {
                    "error": "No models available",
                    "error_code": 503,
                    "context_used": False,
                    "context_items_count": 0,
                    "memory_mode": "public" if remember else "private",
                }
            ),
            503,
        )

    if requested_model and requested_model in available_models:
        model = requested_model
    else:
        model = choose_model(instruction)
        if model not in available_models:
            model = available_models[0]

    context_text = context_data.get("context", "")
    debug_data = context_data.get("debug")
    context_used = bool(context_text.strip())
    if isinstance(debug_data, dict):
        context_items_count = len(debug_data.get("items", []))
    else:
        context_items_count = 0
    file_parts = []
    for name, content in files.items():
        file_parts.append(f"Filename: {name}\n{content}")
    files_text = "\n".join(file_parts)

    full_prompt = (
        context_text
        + "\nInstruction: "
        + instruction
        + "\n\nCode:\n"
        + source_code
        + ("\n" + files_text if files_text else "")
    )
    logger.info("Using model %s for code endpoint", model)

    try:
        proc = subprocess.Popen(
            ["ollama", "run", model],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        proc.stdin.write(full_prompt)
        proc.stdin.close()
        output_lines = []
        for line in proc.stdout:
            output_lines.append(line)
        proc.stdout.close()
        stderr = proc.stderr.read()
        try:
            returncode = proc.wait(timeout=60)
        except subprocess.TimeoutExpired as e:
            proc.kill()
            logger.error("Subprocess timed out: %s", e)
            return (
                jsonify(
                    {
                        "error": "Subprocess timed out",
                        "error_code": 504,
                        "context_used": context_used,
                        "context_items_count": context_items_count,
                        "memory_mode": "public" if remember else "private",
                    }
                ),
                500,
            )
        output_text = "".join(output_lines)
        if returncode != 0:
            raise subprocess.CalledProcessError(
                returncode, proc.args, output=output_text, stderr=stderr
            )
        logger.info("Model %s responded successfully", model)
        return jsonify(
            {
                "response": output_text,
                "context": context_text,
                "debug": debug_data,
                "context_used": context_used,
                "context_items_count": context_items_count,
                "memory_mode": "public" if remember else "private",
                "error_code": 0,
            }
        )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or str(e)
        logger.error("Subprocess failed: %s", error_msg)
        return (
            jsonify(
                {
                    "error": f"Subprocess failed: {error_msg}",
                    "error_code": 500,
                    "context_used": context_used,
                    "context_items_count": context_items_count,
                    "memory_mode": "public" if remember else "private",
                }
            ),
            500,
        )
    except FileNotFoundError as e:
        logger.error("Ollama executable not found: %s", e)
        return (
            jsonify(
                {
                    "error": "Ollama executable not found",
                    "error_code": 500,
                    "context_used": context_used,
                    "context_items_count": context_items_count,
                    "memory_mode": "public" if remember else "private",
                }
            ),
            500,
        )

if __name__ == "__main__":
    threading.Timer(1.0, lambda: webbrowser.open("http://localhost:8000")).start()
    app.run(port=8000)
