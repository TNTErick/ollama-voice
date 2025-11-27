# Ollama-Voice
- A minimal web-app to chat with your OLLAMA.

# Installation

1. Pull this, and sync the venv:
```*sh
uv sync
```
2. Install the ollama model in the venv through `uv run python`:
```python
import ollama
ollama.pull('llama3.2:3b')
```

# Run
```sh
uv run python app.py
```
And the shell output will contain the link to which you can open the web-app.

# Known Issues

- It seems that the model response is from another thread each time.