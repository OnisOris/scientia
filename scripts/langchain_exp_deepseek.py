import os
import time
from dotenv import load_dotenv
from langchain.agents import AgentType, initialize_agent
from langchain_experimental.tools.python.tool import PythonREPLTool
from langchain_openai import ChatOpenAI
from langchain_core.agents import AgentFinish
import json

# Загружаем переменные окружения
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Проверяем наличие API-ключа
if not DEEPSEEK_API_KEY:
    print("❌ DEEPSEEK_API_KEY не найден в .env файле")
    print("🔑 Получите ключ на https://platform.deepseek.com/api-keys")
    exit(1)

# Инициализация DeepSeek
llm = ChatOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1",
    model="deepseek-coder",
    temperature=0,
)

# Инструмент для исполнения Python-кода
python_tool = PythonREPLTool()
tools = [python_tool]


# Кастомный обработчик ошибок парсинга
def handle_parsing_error(error) -> str:
    return f"Ошибка парсинга: {error}. Пожалуйста, переформулируй ответ."


# Создаем агента
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    max_iterations=3,
    handle_parsing_errors=handle_parsing_error,
    return_intermediate_steps=True,
)


# Функция для извлечения Python-кода
def extract_python_code(text: str) -> str:
    if not text:
        return ""

    if "```python" in text:
        start = text.find("```python") + 9
        end = text.find("```", start)
        return text[start:end].strip()

    if "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        return text[start:end].strip()

    return text


# Функция выполнения агента
def run_agent_with_retry(question: str, max_attempts: int = 3):
    for attempt in range(1, max_attempts + 1):
        print(f"\n=== Попытка {attempt}/{max_attempts} ===")
        print(f"Запрос: {question}")

        try:
            start = time.time()
            response = agent.invoke({"input": question})
            elapsed = time.time() - start

            # Извлекаем вывод из промежуточных шагов
            output = ""
            if "intermediate_steps" in response:
                for step in response["intermediate_steps"]:
                    if isinstance(step, tuple) and len(step) >= 2:
                        action, observation = step[:2]
                        if isinstance(action, dict) and "tool_input" in action:
                            output += f"\nДействие: {action['tool']}\nВвод: {action['tool_input']}\n"
                        if observation:
                            output += f"Результат: {observation}\n"

            # Добавляем финальный ответ
            if "output" in response:
                output += f"\nФинальный ответ: {response['output']}"

            print(f"\nВремя выполнения: {elapsed:.2f} сек")
            print("\n=== Полный вывод агента ===")
            print(output)

            # Извлекаем код
            code = ""
            if "intermediate_steps" in response:
                for step in response["intermediate_steps"]:
                    if isinstance(step, tuple) and len(step) >= 1:
                        action = step[0]
                        if isinstance(action, dict) and "tool_input" in action:
                            code_candidate = extract_python_code(
                                str(action["tool_input"])
                            )
                            if code_candidate:
                                code = code_candidate
                                break

            if code:
                print("\n=== Сгенерированный код ===")
                print(code)
            else:
                print("\n[INFO] Код не найден в выводе агента")

            # Проверка результата
            if "120" in output or "факториал" in output.lower():
                print("\n✅ Код выполнен успешно и прошел тест")
                return output
            else:
                raise ValueError("Результат не содержит ожидаемого значения")

        except Exception as e:
            print(f"\n⚠️ Ошибка: {e}")
            if attempt < max_attempts:
                print("🔄 Попытка самокоррекции...")
                question = f"Исправь код на основе ошибки: {str(e)}"
            else:
                print("\n❌ Не удалось после трех попыток")
                return None


# Запуск
if __name__ == "__main__":
    result = run_agent_with_retry(
        "Напиши функцию на Python, которая вычисляет факториал числа n и протестируй её для n=5. \n Формат ответа: только чистый Python-код без дополнительных пояснений"
    )

    if result:
        print("\n" + "=" * 50)
        print("Финальный результат:")
        print(result)
    else:
        print("\nЗадача не выполнена после нескольких попыток")
