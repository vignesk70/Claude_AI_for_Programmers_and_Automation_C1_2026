from openai import OpenAI

from app.core.config import settings

client = OpenAI(
    base_url=settings.ollama_base_url,
    api_key="ollama",  # Ollama doesn't require a real API key
)


def chat(prompt: str, system_prompt: str = "") -> str:
    """Send a prompt to the local Ollama model and return the response text."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=settings.ollama_model,
        messages=messages,
    )
    return response.choices[0].message.content
