import json
import requests
from typing import Any, Optional


class ResponseValidator:
    def __init__(
        self,
        model: str = "qwen2.5-coder:7b",
        ollama_url: str = "http://localhost:11434",
    ):
        self.model = model
        self.ollama_url = ollama_url

    def call_llm(self, prompt: str) -> str:
        """request model returns raw response from ollama"""
        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
        )
        return response.json()["response"]

    def extract_json(self, raw_response: str) -> dict:
        """extract json object from raw response"""
        # find the first { and the last }
        start = raw_response.find("{")
        end = raw_response.rfind("}") + 1
        return json.loads(raw_response[start:end])

    def validate(
        self, raw_response: str, required_fields: list[str]
    ) -> tuple[bool, Optional[dict], Optional[str]]:
        """validate response is a valid json object"""
        try:
            json_obj = self.extract_json(raw_response)
            for field in required_fields:
                if field not in json_obj:
                    return False, None, f"Field {field} is required"
            return True, json_obj, None
        except json.JSONDecodeError:
            return False, None, "Invalid JSON"

    def generate_with_retry(
        self,
        prompt: str,
        required_fields: list[str],
        max_retries: int = 3,
    ) -> dict:
        """
        Вызывает LLM, валидирует JSON, при ошибке повторяет с указанием проблемы.
        Возвращает валидный dict или raises исключение.
        """
        for _ in range(max_retries):
            print(f"++++++Попытка №{max_retries}+++++++")
            raw_response = self.call_llm(prompt)
            is_valid, parsed, error_message = self.validate(
                raw_response, required_fields
            )
            if is_valid:
                return parsed
            else:
                prompt = f"""Твой предыдущий ответ: {raw_response}\n
                Ошибка: {error_message}
                Требуемые поля: {required_fields}
                Верни ТОЛЬКО валидный JSON, без пояснений."""

        raise ValueError(f"Failed to generate valid JSON after {max_retries} retries")


def error_prompt() -> None:
    validator = ResponseValidator()

    # Промпт, который может сбить модель (вернёт текст + JSON)
    prompt = "Объясни, что такое агент в ИИ, и затем верни JSON с полями name, role"

    try:
        result = validator.generate_with_retry(prompt, ["name", "role"], max_retries=2)
        print(f"Успех! Получен JSON: {result}")
    except Exception as e:
        print(f"Не удалось получить валидный JSON: {e}")


def valid_prompt():
    validator = ResponseValidator()
    prompt = "Верни JSON с полями: name (string), role (string). Пример: {'name': 'agent', 'role': 'validator'}"
    print("=== Тест 1: запрос к LLM ===")
    raw = validator.call_llm(prompt)
    print(f"Ответ LLM:\n{raw}\n")

    is_valid, parsed, error = validator.validate(raw, required_fields=["name", "role"])
    print(f"Валидный JSON: {is_valid}")
    if is_valid:
        print(f"Распарсено: {parsed}")
    else:
        print(f"Ошибка: {error}")


if __name__ == "__main__":
    valid_prompt()
    error_prompt()
