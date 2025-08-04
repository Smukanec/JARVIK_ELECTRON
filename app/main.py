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

    response = subprocess.run(
        ["ollama", "run", model],
        input=full_prompt.encode(),
        capture_output=True
    )
    return jsonify({"response": response.stdout.decode()})

if __name__ == "__main__":
    app.run(port=8000)