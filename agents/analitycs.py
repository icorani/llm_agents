# analyzer.py
import json
from validator import ResponseValidator


class NodeRedAnalyzer:
    def __init__(self, model: str = "qwen2.5-coder:7b"):
        self.validator = ResponseValidator(model=model)
        self.system_prompt = """
Ты эксперт по Node-RED. Анализируй JSON flow и возвращай строго JSON со следующей структурой:

{
    "nodes": [
        {
            "id": "идентификатор",
            "type": "тип_узла", 
            "name": "имя_узла",
            "config": {"специфичные_поля": "значения"}
        }
    ],
    "connections": [
        {"from": "id_узла", "to": "id_узла"}
    ],
    "entry_points": ["id_узла_без_входящих_связей"],
    "exit_points": ["id_узла_без_исходящих_связей"],
    "summary": "краткое описание логики",
    "errors": "обнаруженные ошибки",
    "warnings": "предупреждения о нестыковках в логике предоставленных данных"
}

Правила:
1. В config включай ТОЛЬКО специфичные поля узла (не id, type, name, wires)
2. Для function-узлов бери весь код из поля "func"
3. Для mqtt in/out бери topic, qos
4. Для http request бери url, method
5. Для inject бери repeat, payload
6. Возвращай ТОЛЬКО JSON, без пояснений
7. Если в connections встречается узел, которого нет в nodes — добавь поле "errors": ["Узел 'normal' не найден в nodes"]
8. Если у узла есть исходящие связи, но нет целевого узла — добавь ошибку
9. Если узел висячий (нет входящих, но не entry_point) — добавь предупреждение
10. В конце ответа должны быть поля "warnings" и "errors" (массивы строк) если ошибок нет, то null
11. Не добавляй ничего от себя - все данные должны браться только из предоставленной информации.
"""

    def analyze(self, flow: list) -> dict:
        """Анализирует Node-RED flow и возвращает структурированное описание"""

        user_prompt = f"Проанализируй этот Node-RED flow:\n{json.dumps(flow, indent=2)}"

        result = self.validator.generate_with_retry_and_sys_prompt(
            user_prompt=user_prompt,
            required_fields=[
                "nodes",
                "connections",
                "entry_points",
                "exit_points",
                "summary",
            ],
            system_prompt=self.system_prompt,
            max_retries=3,
        )

        return result


if __name__ == "__main__":
    # Тестовый flow
    test_flow = [
        {
            "id": "inject1",
            "type": "inject",
            "name": "Ежечасный триггер",
            "payload": "",
            "repeat": "3600",
            "wires": [["http1"]],
        },
        {
            "id": "http1",
            "type": "http request",
            "name": "Запрос погоды",
            "url": "https://api.weather.com/current",
            "method": "GET",
            "wires": [["function1"]],
        },
        {
            "id": "function1",
            "type": "function",
            "name": "Парсинг ответа",
            "func": "msg.temperature = msg.payload.main.temp; msg.city = msg.payload.name; return msg;",
            "wires": [["switch1"]],
        },
        {
            "id": "mqtt1",
            "type": "mqtt out",
            "name": "Публикация",
            "topic": "weather/current",
            "qos": "1",
            "wires": [],
        },
        {
            "id": "switch1",
            "type": "switch",
            "property": "payload.temperature",
            "rules": [{"t": "gt", "v": 30, "vt": "num"}, {"t": "otherwise"}],
            "wires": [["mqtt1"], ["normal"]],
        },
    ]

    analyzer = NodeRedAnalyzer()
    result = analyzer.analyze(test_flow)
    print(json.dumps(result, indent=2, ensure_ascii=False))
