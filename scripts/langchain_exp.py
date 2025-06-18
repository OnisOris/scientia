# Убедитесь, что установлены все зависимости:
# pip install langgraph langchain-openai langchain-experimental python-dotenv

import operator
import os
from typing import Annotated, Sequence, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage

# Загружаем переменные окружения
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Импорт современных компонентов LangChain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_experimental.tools.python.tool import PythonREPLTool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode


# Определяем состояние агента
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    input: str
    agent_scratchpad: Annotated[Sequence[BaseMessage], operator.add]
    next: str


# Инициализация LLM
llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo", api_key=OPENAI_API_KEY)

# Создаем инструменты
tools = [PythonREPLTool()]

# Создаем промпт для агента
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Ты экспертный программист Python. Используй Python REPL для выполнения и тестирования кода.",
        ),
        MessagesPlaceholder(variable_name="messages"),
        ("user", "Текущая задача: {input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

# Создаем LLM-агент через функциональный конвейер
agent = prompt | llm.bind_tools(tools)


# Функция перехода для графа
def should_continue(state: AgentState) -> str:
    messages = state["messages"]
    last_message = messages[-1]
    # Если есть вызовы инструментов, запускаем ToolNode
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "action"
    return "end"


# Создаем граф
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent)
workflow.add_node("action", ToolNode(tools))
workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent", should_continue, {"action": "action", "end": END}
)
workflow.add_edge("action", "agent")
app = workflow.compile()


# Функция выполнения агента с самокоррекцией
def run_agent_with_retry(question: str, max_attempts: int = 3):
    for attempt in range(max_attempts):
        try:
            # Передаем все нужные поля, включая input
            response = app.invoke(
                {
                    "messages": [HumanMessage(content=question)],
                    "input": question,
                    "agent_scratchpad": [],
                }
            )
            # Последнее сообщение агента
            output = response["messages"][-1].content
            print(f"\n--- Результат (попытка {attempt + 1}) ---\n{output}")

            # Проверяем результат
            if (
                any(val in output for val in ["120", "3628800"])
                or "факториал" in output.lower()
            ):
                print("\n✅ Код выполнен успешно и прошел тест")
                return output
            else:
                raise ValueError("Результат не содержит ожидаемого значения")
        except Exception as e:
            print(f"\n⚠️ Ошибка: {e}")
            if attempt < max_attempts - 1:
                print("🔄 Агент пытается исправить ошибку...")
                question = f"Исправь ошибку в предыдущем коде: {e}"
            else:
                print("\n❌ Не удалось выполнить задачу после 3 попыток")
                raise


# Точка входа
if __name__ == "__main__":
    question = "Напиши функцию на Python, которая вычисляет факториал числа n и протестируй её для n=5."
    run_agent_with_retry(question)
