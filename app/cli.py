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

        # verify files are accessible before starting upload
        for path in [main_file] + extra_files:
            try:
                with open(path, "r", encoding="utf-8"):
                    pass
            except OSError as e:
                print(f"Cannot read {path}: {e}")
                return

        def stream_payload():
            yield '{"code":"'
            try:
                with open(main_file, "r", encoding="utf-8") as f:
                    for chunk in iter(lambda: f.read(65536), ''):
                        yield json.dumps(chunk)[1:-1]
            except OSError as e:
                raise RuntimeError(f"Cannot read {main_file}: {e}") from e
            yield '","instruction":'
            yield json.dumps(instruction)
            yield ',"files":{'
            for idx, path in enumerate(extra_files):
                if idx:
                    yield ','
                name = os.path.basename(path)
                yield json.dumps(name)
                yield ':"'
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for chunk in iter(lambda: f.read(65536), ''):
                            yield json.dumps(chunk)[1:-1]
                except OSError as e:
                    raise RuntimeError(f"Cannot read {path}: {e}") from e
                yield '"'
            yield '},"api_url":'
            yield json.dumps(self.api_url or None)
            yield ',"username":'
            yield json.dumps(self.username)
            yield ',"api_key":'
            yield json.dumps(self.api_key)
            yield ',"model":'
            yield json.dumps(self.model or None)
            yield ',"remember":'
            yield json.dumps(self.memory == "public")
            yield '}'

        headers = {"Content-Type": "application/json"}
        try:
            res = requests.post(
                f"{BASE_URL}/code",
                data=stream_payload(),
                headers=headers,
                timeout=120,
            )
            data = res.json()
            if res.ok:
                self._print_response(data)
            else:
                print("Error:", data.get("error", res.text))
        except RuntimeError as e:
            print(e)
        except Exception as e:
            print("Request failed:", e)

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
