import json
import networkx as nx


class Pathfinding:
    def __init__(self, graph_file):
        self.graph = nx.Graph()
        self.load_graph(graph_file)

    def load_graph(self, graph_file):
        with open(graph_file, "r") as file:
            data = json.load(file)

        for node, pos in data["nodes"].items():
            self.graph.add_node(node, pos=pos)

        for edge in data["edges"]:
            self.graph.add_edge(*edge)

    def find_path(self, start, end):
        return nx.astar_path(self.graph, start, end)


if __name__ == "__main__":
    pf = Pathfinding("data/graph.json")
    path = pf.find_path("A", "C")
    print("Path:", path)

