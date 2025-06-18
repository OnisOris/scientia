import operator
import os
import time
from typing import Annotated, Sequence, TypedDict

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Проверяем наличие API-ключа
if not DEEPSEEK_API_KEY:
    print("❌ DEEPSEEK_API_KEY не найден в .env файле")
    print("🔑 Получите ключ на https://platform.deepseek.com/api-keys")
    exit(1)

# Импорт компонентов LangGraph
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_experimental.tools.python.tool import PythonREPLTool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

# Инициализация DeepSeek через OpenAI-совместимый интерфейс
llm = ChatOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1",
    model="deepseek-coder",
    temperature=0,
)

# Инструмент для исполнения Python-кода
python_tool = PythonREPLTool()
tools = [python_tool]


# Определяем состояние агента
class AgentState(TypedDict):
    input: str
    messages: Annotated[Sequence[BaseMessage], operator.add]


# Создаем промпт с четкими инструкциями
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "Ты экспертный программист Python. Отвечай ТОЛЬКО кодом на Python.\n"
                "Формат ответа: ```python\n<код>\n```\n"
                "После генерации кода он будет автоматически выполнен."
            ),
        ),
        ("user", "{input}"),
    ]
)

# Создаем цепочку для агента
agent_chain = (
    RunnablePassthrough.assign(input=lambda x: x["input"]) | prompt | llm
)


# Создаем функцию для узла агента
def run_agent_node(state: AgentState):
    result = agent_chain.invoke(state)
    return {"messages": [result]}


# Создаем функцию для узла инструмента
def run_tool_node(state: AgentState):
    last_message = state["messages"][-1]
    code = extract_python_code(last_message.content)

    if not code:
        return {
            "messages": [
                HumanMessage(
                    content="Не удалось извлечь код для выполнения. Пожалуйста, предоставьте код в формате ```python"
                )
            ]
        }

    try:
        result = python_tool.run(code)
        return {"messages": [HumanMessage(content=result)]}
    except Exception as e:
        return {
            "messages": [HumanMessage(content=f"Ошибка выполнения: {str(e)}")]
        }


# Создаем граф
workflow = StateGraph(AgentState)

# Добавляем узлы
workflow.add_node("agent", run_agent_node)
workflow.add_node("tool", run_tool_node)

# Устанавливаем связи
workflow.set_entry_point("agent")
workflow.add_edge("agent", "tool")
workflow.add_edge("tool", END)

# Компилируем граф
app = workflow.compile()


# Функция для извлечения Python-кода из сообщения
def extract_python_code(text: str) -> str:
    """Извлекает Python-код из текста ответа"""
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
            # Создаем начальное состояние
            state = {
                "input": question,
                "messages": [
                    HumanMessage(
                        content=question
                        + "\n\nФормат ответа: ТОЛЬКО Python-код в блоке ```python\n<код>\n```"
                    )
                ],
            }

            # Выполняем граф
            start_time = time.time()
            response = app.invoke(state)
            elapsed = time.time() - start_time

            # Обрабатываем результат
            output = ""
            for msg in response["messages"]:
                if hasattr(msg, "content"):
                    output += f"{msg.content}\n"

            print(f"\nВремя выполнения: {elapsed:.2f} сек")
            print("\n=== Результат выполнения ===")
            print(output)

            # Извлекаем код
            code = extract_python_code(output)
            if code:
                print("\n=== Сгенерированный код ===")
                print(code)
            else:
                print("\n[INFO] Код не найден в выводе агента")

            # Проверка результата
            if "120" in output:
                print("\n✅ Код выполнен успешно и прошел тест")
                return output
            else:
                raise ValueError(
                    "Результат не содержит ожидаемого значения '120'"
                )

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
    # Четкий запрос
    question = "Напиши функцию на Python, которая вычисляет факториал числа n и протестируй её для n=5."

    result = run_agent_with_retry(question)

    if result:
        print("\n" + "=" * 50)
        print("Финальный результат выполнения:")
        print(result)
    else:
        print("\nЗадача не выполнена после нескольких попыток")
