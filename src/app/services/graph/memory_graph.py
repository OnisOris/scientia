# app/services/graph/memory_graph.py
import networkx as nx
import numpy as np
import umap.umap_ as umap
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity


class MemoryGraph:
    def __init__(self, embeddings: list[list[float]]):
        self.graph = nx.Graph()
        self.embeddings = embeddings
        # Добавляем узлы в граф
        for i, vec in enumerate(embeddings):
            self.graph.add_node(i, embedding=vec)

    def build_edges(self, threshold: float = 0.7):
        # Строим ребра по схожести (cosine similarity)
        X = np.array(self.embeddings)
        sims = cosine_similarity(X)
        n = len(self.embeddings)
        for i in range(n):
            for j in range(i + 1, n):
                if sims[i][j] > threshold:
                    self.graph.add_edge(i, j, weight=float(sims[i][j]))

    def reduce_dim(self, method: str = "umap"):
        # Снижаем размерность эмбеддингов для визуализации
        arr = np.array(self.embeddings)
        if method == "pca":
            reducer = PCA(n_components=2)
        else:
            reducer = umap.UMAP(n_components=2)
        coords = reducer.fit_transform(arr)
        # Сохраняем координаты в узлах
        for idx, coord in enumerate(coords):
            self.graph.nodes[idx]["pos"] = coord.tolist()

    def get_positions(self):
        # Возвращает словарь {node: [x, y]}
        return {
            i: data.get("pos", [0, 0])
            for i, data in self.graph.nodes(data=True)
        }
