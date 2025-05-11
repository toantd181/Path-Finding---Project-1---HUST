import sqlite3  # Import the sqlite3 module
import networkx as nx
import os  # Import os to check if file exists


class Pathfinding:
    def __init__(self, graph_db_path):
        # Use DiGraph for directed graph
        self.graph = nx.DiGraph()
        if not os.path.exists(graph_db_path):
            raise FileNotFoundError(f"Database file not found: {graph_db_path}")
        self.load_graph_from_db(graph_db_path)

    def load_graph_from_db(self, db_path):
        """Loads graph data from an SQLite database."""
        conn = None  # Initialize conn to None
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Load nodes
            cursor.execute("SELECT name, x, y FROM nodes")
            nodes = cursor.fetchall()
            for node_name, x, y in nodes:
                # Store position as a tuple in the 'pos' attribute
                self.graph.add_node(node_name, pos=(x, y))

            # Load edges
            cursor.execute("SELECT node_from, node_to, weight FROM edges")
            edges = cursor.fetchall()
            for node_from, node_to, weight in edges:
                # Add directed edge with weight attribute
                self.graph.add_edge(node_from, node_to, weight=weight)

        except sqlite3.Error as e:
            print(f"SQLite error: {e}")
            # Handle error appropriately, maybe raise an exception
        finally:
            if conn:
                conn.close()  # Ensure connection is closed even if errors occur

    def find_path(self, start_node, end_node):
        """Finds the shortest path using A* algorithm."""
        # A* needs a heuristic function, typically distance.
        # We'll use Euclidean distance based on 'pos' attribute.
        def heuristic(u, v):
            # Check if nodes exist before accessing attributes
            if u not in self.graph.nodes or v not in self.graph.nodes:
                 # Handle cases where heuristic is called on non-existent nodes if necessary
                 # This might happen depending on the algorithm's internal workings
                 # For A*, it usually operates on existing nodes, but safety check is good.
                 return float('inf') # Or some other appropriate value/error handling

            if 'pos' not in self.graph.nodes[u] or 'pos' not in self.graph.nodes[v]:
                print(f"Warning: 'pos' attribute missing for node {u} or {v}")
                return float('inf') # Cannot calculate heuristic without position

            pos_u = self.graph.nodes[u]['pos']
            pos_v = self.graph.nodes[v]['pos']
            # Ensure positions are valid numbers
            if not all(isinstance(coord, (int, float)) for coord in pos_u + pos_v):
                 print(f"Warning: Invalid position data for nodes {u} or {v}")
                 return float('inf')

            return ((pos_u[0] - pos_v[0])**2 + (pos_u[1] - pos_v[1])**2)**0.5

        try:
            # Check if start and end nodes exist in the graph
            if start_node not in self.graph:
                print(f"Error: Start node '{start_node}' not found in the graph.")
                return None
            if end_node not in self.graph:
                print(f"Error: End node '{end_node}' not found in the graph.")
                return None

            # Use 'weight' attribute for edge costs and the heuristic function
            # A* works correctly with DiGraph
            path = nx.astar_path(self.graph, start_node, end_node, heuristic=heuristic, weight='weight')
            return path
        except nx.NetworkXNoPath:
            print(f"No path found between {start_node} and {end_node}")
            return None
        except KeyError as e:
            # This might still catch issues if heuristic accesses a non-existent node attribute
            # despite checks inside heuristic, depending on exact execution flow.
            print(f"Error: Attribute access issue for node {e} during pathfinding.")
            return None
        except Exception as e: # Catch other potential errors
            print(f"An unexpected error occurred during pathfinding: {e}")
            return None


