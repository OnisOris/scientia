import os
import time

from dotenv import load_dotenv
from langchain.agents import AgentType, initialize_agent
from langchain_experimental.tools.python.tool import PythonREPLTool

# Импорт компонентов LangChain
from langchain_openai import ChatOpenAI

# Загружаем переменные окружения
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Инициализация LLM
llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo", api_key=OPENAI_API_KEY)

# Инструмент для исполнения Python-кода
python_tool = PythonREPLTool()
tools = [python_tool]

# Создаем агента с реактивной стратегией
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
)


# Функция для извлечения Python-кода из сообщения
def extract_python_code(text: str) -> str:
    if "```python" in text:
        start = text.find("```python") + len("```python")
        end = text.find("```", start)
        return text[start:end].strip()
    return ""


# Функция выполнения агента с логированием и самокоррекцией
def run_agent_with_retry(question: str, max_attempts: int = 3):
    for attempt in range(1, max_attempts + 1):
        print(f"\n=== Попытка {attempt}/{max_attempts} ===")
        print(f"Запрос: {question}\n")
        try:
            start = time.time()
            response = agent.run(question)
            elapsed = time.time() - start

            print(f"Время выполнения: {elapsed:.2f} сек")
            print("\n=== Ответ агента ===")
            print(response)

            code = extract_python_code(response)
            if code:
                print("\n=== Сгенерированный код ===")
                print(code)

            # Проверка результата
            if (
                any(val in response for val in ["120", "3628800"])
                or "факториал" in response.lower()
            ):
                print("\n✅ Код выполнен успешно и прошел тест")
                return
            else:
                raise ValueError("Результат не содержит ожидаемого значения")
        except Exception as e:
            print(f"\n⚠️ Ошибка: {e}")
            if attempt < max_attempts:
                print("🔄 Попытка самокоррекции...")
                question = (
                    f"Исправь код, чтобы он прошел тест на факториал: {e}"
                )
            else:
                print("\n❌ Не удалось после трех попыток")


# Запуск
if __name__ == "__main__":
    run_agent_with_retry(
        "Напиши функцию на Python, которая вычисляет факториал числа n и протестируй её для n=5."
    )
