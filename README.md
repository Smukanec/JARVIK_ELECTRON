# Jarvik Electron UI

## Instalace

1. **Node.js & npm**  
   - Stáhněte a nainstalujte aktuální verzi z [nodejs.org](https://nodejs.org/).  
   - Ověřte v terminálu příkazy `node -v` a `npm -v`, že jsou dostupné.

2. **Elektronové závislosti**  
   ```bash
   cd JARVIK_ELECTRON
   npm install
   ```  
   - Tím se nainstaluje `electron` a `electron-builder` definované v `package.json`.

3. **Python a knihovny**
   - Ujistěte se, že máte Python 3 a pip (`python --version`, `pip --version`).
   - Nainstalujte závislosti projektu:
     ```bash
     pip install -r requirements.txt
     ```

4. **Ollama a modely**  
   - Nainstalujte [Ollama](https://ollama.com/) (podle OS).  
   - Stáhněte modely používané aplikací:  
     ```bash
     ollama pull phi3
     ollama pull llama3
     ollama pull mistral
     ```

5. **API klíče**  
   - Aplikace potřebuje proměnné prostředí `API_KEY` a `USERNAME` pro službu "fura".
   - Proměnné lze uložit do souboru `.env` nebo je nastavit ručně, např. na Linux/macOS:
     ```bash
     export API_KEY="váš_token"
     export USERNAME="vaše_uživatelské_jméno"
     ```

## Spuštění

1. V kořenové složce projektu spusťte:
   ```bash
   npm start
   ```
   - Spustí se Electron a automaticky i lokální Flask server (`app/main.py`).

2. V otevřeném okně aplikace zadejte dotaz do textového pole a stiskněte **Odeslat**.  
   - Dotaz se odešle na lokální Flask backend, ten zvolí model (`phi3`, `llama3`, `mistral`) a přes `ollama` vygeneruje odpověď.

3. **Ukončení**  
   - Zavřete okno aplikace; Electron i Flask proces se ukončí.

## Distribuce (volitelně)

- Pro vytvoření instalačního balíčku:
  ```bash
  npm run dist
  ```
  Vygeneruje se balíček podle nastavení `electron-builder`.

## Jarvik.exe na Windows

Chcete‑li spustit backend jako samostatnou aplikaci na Windows:

1. V příkazovém řádku nainstalujte Python závislosti:
   ```bash
   pip install -r requirements.txt
   ```
2. Vytvořte spustitelný soubor pomocí PyInstalleru:
   ```bash
   pyinstaller Jarvik.spec
   ```
   V adresáři `dist` se objeví `Jarvik.exe`.
3. Před spuštěním nezapomeňte nastavit proměnné prostředí `API_KEY` a `USERNAME` a mít nainstalovaný [Ollama](https://ollama.com/) s potřebnými modely.

## Popis

Toto je desktopová aplikace (Electron), která poskytuje rozhraní k lokálnímu asistentovi Jarvik běžícímu na `http://localhost:8000`. Je třeba, aby backend (Flask/Ollama) běžel před spuštěním této aplikace.

### UI funkce

- Zobrazuje vrácený kontext a ladicí informace.
- Umožňuje volit mezi soukromou a veřejnou pamětí při dotazu.
- Nabízí popis dostupných modelů pro snadnější orientaci.

## CLI rozhraní (bez prohlížeče)

Aplikaci lze ovládat i z příkazové řádky pomocí skriptu `app/cli.py`.
Nejprve spusťte backend (`python app/main.py` nebo `npm start` podle instrukcí výše)
a v jiném terminálu zadejte:

```bash
python app/cli.py
```

Základní příkazy v interaktivním režimu:

- `login <api_url> <username> <api_key>` – uloží přihlašovací údaje a načte dostupné modely.
- `ask <dotaz>` – odešle dotaz na server a vypíše odpověď, kontext i ladicí informace.
- `code <soubor> <instrukce> [další_soubor ...]` – odešle kód a volitelné dodatečné soubory pro zpracování.
- `models`, `setmodel <model>` – vypíše nebo nastaví používaný model.
- `setmemory <private|public>` – volba paměti.
- `exit` – ukončení rozhraní.

Tímto je možné používat Jarvik bez webového prohlížeče.
