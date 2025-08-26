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
   - Nainstalujte Flask, Requests a python-dotenv:
     ```bash
     pip install flask requests python-dotenv
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

## Popis

Toto je desktopová aplikace (Electron), která poskytuje rozhraní k lokálnímu asistentovi Jarvik běžícímu na `http://localhost:8000`. Je třeba, aby backend (Flask/Ollama) běžel před spuštěním této aplikace.
