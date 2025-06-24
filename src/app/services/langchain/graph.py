# app/services/langchain/graph.py
from langchain.chains.graph_qa import GraphQAChain
from langchain import LLMChain
from langchain.graphs.networkx_graph import NetworkxEntityGraph


class GraphChainFactory:
    @staticmethod
    def create_graph_qa(entity_chain: LLMChain, qa_chain: LLMChain, nx_graph):
        # Конвертируем networkx граф в формат LangChain
        graph = NetworkxEntityGraph(nx_graph)
        graph_qa = GraphQAChain(
            entity_extraction_chain=entity_chain,
            graph=graph,
            qa_chain=qa_chain,
        )
        return graph_qa
