import json
from typing import Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from app.config import get_settings

T = TypeVar("T", bound=BaseModel)


def get_openai_client() -> OpenAI:
    settings = get_settings()
    return OpenAI(base_url=settings.llm_base_url, api_key=settings.groq_api_key or "not-set")


def chat_completion(messages: list[dict[str, str]], *, temperature: float = 0.2) -> str:
    settings = get_settings()
    client = get_openai_client()
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content or ""


def structured_output(model_cls: type[T], messages: list[dict[str, str]]) -> T:
    settings = get_settings()
    client = get_openai_client()
    schema = model_cls.model_json_schema()
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=0,
        response_format={
            "type": "json_schema",
            "json_schema": {"name": model_cls.__name__, "schema": schema},
        },
    )
    raw = resp.choices[0].message.content or "{}"
    data = json.loads(raw)
    return model_cls.model_validate(data)
