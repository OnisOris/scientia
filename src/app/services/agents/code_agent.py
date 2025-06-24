# app/services/agents/code_agent.py
from app.services.agents.base import AgentBase
import subprocess


class CodeAgent(AgentBase):
    async def run(self, code: str) -> str:
        # Запускаем Python-код в отдельном процессе (осторожно с безопасностью)
        try:
            result = subprocess.run(
                ["python3", "-c", code],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout or result.stderr
        except Exception as e:
            return str(e)
