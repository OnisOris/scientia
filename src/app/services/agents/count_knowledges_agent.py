from typing import List, Optional

from app.services.agents.base import AgentBase


class KnowledgesAgent(AgentBase):
    def __init__(self):
        """
        :param ...
        """
        self.embeddings: Optional[List] = None

    def get_embeddings(self):
        """
        Забирает ембеддинги и обрабатывает, сохраняет все в поле класса
        """
        pass

    def memory_factory(self) -> None:
        """
        Основная обработка ембедингов.

        Рассчеты времени, когда повторять данное понятие, корректировака коэффициента убывания памяти
        (для каждого человека он индивидуальный), формирование траектории обучения, пересчет коэффициента памяти
        данного понятия (он должен загрузиться обратно в weaviate, обновив вес памяти)
        """

    def coeffs_upload(self) -> None:
        """
        Функция обновляет веса обрабатываемых понятий в векторной базе данных
        """
