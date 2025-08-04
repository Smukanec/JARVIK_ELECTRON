def choose_model(prompt):
    prompt = prompt.lower()
    if "program" in prompt or "kód" in prompt:
        return "phi3"
    elif "právo" in prompt or "smlouva" in prompt:
        return "llama3"
    else:
        return "mistral"