import cmd
import json
import os
import shlex
import requests

BASE_URL = "http://localhost:8000"

class JarvikCLI(cmd.Cmd):
    intro = "Jarvik CLI - type help or ? to list commands."
    prompt = "Jarvik> "

    def __init__(self):
        super().__init__()
        self.api_url = ""
        self.username = ""
        self.api_key = ""
        self.model = ""
        self.memory = "private"
        self.models = []

    # --- helper methods -------------------------------------------------
    def _require_login(self):
        if not self.api_key or not self.username:
            print("Please login first (login <api_url> <username> <api_key>)")
            return False
        return True

    def _fetch_models(self):
        try:
            res = requests.get(f"{BASE_URL}/models", timeout=10)
            res.raise_for_status()
            self.models = res.json()
            if self.models and self.model not in self.models:
                self.model = self.models[0]
            print("Available models:", ", ".join(self.models) or "<none>")
            if self.model:
                print("Current model:", self.model)
        except Exception as e:
            print("Failed to fetch models:", e)

    def _print_response(self, data):
        if "response" in data:
            print("\nResponse:\n" + data["response"])
        if data.get("context"):
            print("\nContext:\n" + data["context"])
        if data.get("debug"):
            dbg = data["debug"]
            if isinstance(dbg, dict):
                dbg = json.dumps(dbg, indent=2)
            print("\nDebug:\n" + str(dbg))

    # --- commands -------------------------------------------------------
    def do_login(self, line):
        """login <api_url> <username> <api_key>
        Store credentials for subsequent requests."""
        parts = shlex.split(line)
        if len(parts) < 3:
            print("Usage: login <api_url> <username> <api_key>")
            return
        self.api_url, self.username, self.api_key = parts[:3]
        print(f"Logged in as {self.username}")
        self._fetch_models()

    def do_logout(self, line):
        """Clear stored credentials"""
        self.api_url = ""
        self.username = ""
        self.api_key = ""
        print("Logged out")

    def do_models(self, line):
        """List available models from server"""
        self._fetch_models()

    def do_setmodel(self, line):
        """setmodel <model>
        Choose model for subsequent requests."""
        model = line.strip()
        if not model:
            print("Usage: setmodel <model>")
            return
        if self.models and model not in self.models:
            print(f"Model '{model}' not in available models: {', '.join(self.models)}")
            return
        self.model = model
        print("Current model:", self.model)

    def do_setmemory(self, line):
        """setmemory <private|public>
        Choose memory scope for requests."""
        mem = line.strip().lower()
        if mem not in {"private", "public"}:
            print("Usage: setmemory <private|public>")
            return
        self.memory = mem
        print("Current memory:", self.memory)

    def do_ask(self, line):
        """ask <message>
        Send a question to the server."""
        if not self._require_login():
            return
        message = line.strip()
        if not message:
            print("Usage: ask <message>")
            return
        payload = {
            "message": message,
            "api_url": self.api_url or None,
            "username": self.username,
            "api_key": self.api_key,
            "model": self.model or None,
            "remember": self.memory == "public",
        }
        try:
            res = requests.post(f"{BASE_URL}/ask", json=payload, timeout=120)
            data = res.json()
            if res.ok:
                self._print_response(data)
            else:
                print("Error:", data.get("error", res.text))
        except Exception as e:
            print("Request failed:", e)

    def do_code(self, line):
        """code <file> <instruction> [extra_file ...]
        Send code file with instruction. Additional files can follow."""
        if not self._require_login():
            return
        parts = shlex.split(line)
        if len(parts) < 2:
            print("Usage: code <file> <instruction> [extra_file ...]")
            return
        main_file = parts[0]
        instruction = parts[1]
        extra_files = parts[2:]
        header = {
            "instruction": instruction,
            "api_url": self.api_url or None,
            "username": self.username,
            "api_key": self.api_key,
            "model": self.model or None,
            "remember": self.memory == "public",
        }

        def stream_files():
            yield json.dumps(header).encode("utf-8") + b"\n"
            paths = [(main_file, os.path.basename(main_file))]
            paths += [(p, os.path.basename(p)) for p in extra_files]
            for path, name in paths:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for chunk in iter(lambda: f.read(65536), ""):
                            block = {"file": name, "code": chunk}
                            yield json.dumps(block).encode("utf-8") + b"\n"
                except OSError as e:
                    err_block = {"error": f"Cannot read {path}: {e}"}
                    yield json.dumps(err_block).encode("utf-8") + b"\n"
                    return

        try:
            res = requests.post(
                f"{BASE_URL}/code",
                data=stream_files(),
                headers={"Content-Type": "application/x-ndjson"},
                timeout=120,
            )
            data = res.json()
            if res.ok:
                self._print_response(data)
            else:
                print("Error:", data.get("error", res.text))
        except requests.RequestException as e:
            print("Request failed:", e)
        except ValueError:
            print("Invalid JSON response from server")

    def do_exit(self, line):
        """Exit the CLI"""
        print("Bye")
        return True

    def do_quit(self, line):
        return self.do_exit(line)

    def emptyline(self):
        pass

if __name__ == "__main__":
    JarvikCLI().cmdloop()
