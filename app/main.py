from flask import Flask, request, jsonify
import subprocess
from fura_client import get_context
from model_router import choose_model

app = Flask(__name__)

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    query = data["message"]
    context_data = get_context(query)
    model = choose_model(query)
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
    app.run(port=8000)
