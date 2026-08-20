from openai import OpenAI

from app.core.config import settings

client = OpenAI(
    base_url=settings.ollama_base_url,
    api_key="ollama",  # Ollama doesn't require a real API key
)


def chat(
    prompt: str,
    system_prompt: str = "",
    max_tokens: int | None = None,
    response_format: str | None = None,
) -> dict:
    """Send a prompt to the local Ollama model and return the response text with token usage."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    kwargs = {"model": settings.ollama_model, "messages": messages}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if response_format is not None:
        kwargs["response_format"] = {"type": response_format}

    response = client.chat.completions.create(**kwargs)

    return {
        "response": response.choices[0].message.content,
        "input_tokens": response.usage.prompt_tokens if response.usage else None,
        "output_tokens": response.usage.completion_tokens if response.usage else None,
    }
