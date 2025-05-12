import sqlite3
import networkx as nx
import os


class Pathfinding:
    def __init__(self, graph_db_path):
        self.graph = nx.DiGraph()
        self.db_path = graph_db_path
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found: {self.db_path}")
        self.load_graph_from_db(self.db_path)

    def load_graph_from_db(self, db_path):
        """Loads graph data from an SQLite database, ensuring data integrity for positions."""
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            # Optional: Enforce foreign keys if they are defined in the schema and you want SQLite to check them.
            # cursor.execute("PRAGMA foreign_keys = ON;")

            # Load nodes from the 'nodes' table and store their names.
            # Only these nodes will be considered valid and have a 'pos' attribute.
            valid_node_names_with_pos = set()
            cursor.execute("SELECT name, x, y FROM nodes")
            nodes_data = cursor.fetchall()
            
            if not nodes_data:
                print("Warning: No nodes found in the 'nodes' table.")

            for node_name, x, y in nodes_data:
                if x is None or y is None:
                    print(f"Warning: Node '{node_name}' from 'nodes' table has NULL/missing coordinates. Skipping this node.")
                    continue
                try:
                    pos_x = float(x)
                    pos_y = float(y)
                    self.graph.add_node(node_name, pos=(pos_x, pos_y))
                    valid_node_names_with_pos.add(node_name)
                except ValueError:
                    print(f"Warning: Node '{node_name}' has invalid (non-numeric) coordinates '{x}, {y}'. Skipping this node.")
            
            print(f"Successfully loaded {len(valid_node_names_with_pos)} nodes with valid positions from 'nodes' table.")

            # Load edges, ensuring they only connect valid nodes (those with positions).
            cursor.execute("SELECT node_from, node_to, weight FROM edges")
            edges_data = cursor.fetchall()
            edges_added_count = 0
            
            if not edges_data and len(valid_node_names_with_pos) > 0 : # Only warn if nodes exist but no edges
                print("Warning: No edges found in the 'edges' table.")

            for node_from, node_to, weight in edges_data:
                if node_from in valid_node_names_with_pos and node_to in valid_node_names_with_pos:
                    if weight is None:
                        print(f"Warning: Edge ('{node_from}' -> '{node_to}') has NULL/missing weight. Skipping this edge.")
                        continue
                    try:
                        edge_weight = float(weight)
                        self.graph.add_edge(node_from, node_to, weight=edge_weight)
                        edges_added_count += 1
                    except ValueError:
                        print(f"Warning: Edge ('{node_from}' -> '{node_to}') has invalid (non-numeric) weight '{weight}'. Skipping this edge.")
                else:
                    if node_from not in valid_node_names_with_pos:
                        print(f"Warning: Edge ('{node_from}' -> '{node_to}') references source node '{node_from}' which is not in 'nodes' table or has invalid/missing coordinates. Skipping edge.")
                    if node_to not in valid_node_names_with_pos:
                        # This condition might be redundant if the first one caught it, but good for clarity
                        print(f"Warning: Edge ('{node_from}' -> '{node_to}') references target node '{node_to}' which is not in 'nodes' table or has invalid/missing coordinates. Skipping edge.")
            
            print(f"Successfully loaded {edges_added_count} valid edges from 'edges' table.")

        except sqlite3.Error as e:
            print(f"SQLite error during graph loading: {e}")
        except Exception as e: # Catch any other unexpected errors during loading
            print(f"An unexpected error occurred during graph loading: {e}")
        finally:
            if conn:
                conn.close()

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

    def get_all_searchable_locations(self):
        """
        Fetches all node names and special place names from the database.
        Returns a list of dictionaries, each with 'display_name', 'search_term', 
        'type', 'id', and 'pos'.
        'id' for nodes is the node_id.
        'id' for special_places is their specific ID from the table.
        'pos' is (x,y) tuple.
        """
        locations = []
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Fetch nodes
            cursor.execute("SELECT name, x, y FROM nodes")
            nodes = cursor.fetchall()
            for node_name, x, y in nodes:
                locations.append({
                    'display_name': f"{node_name} (Node)",
                    'search_term': node_name.lower(), # For case-insensitive search matching
                    'type': 'node',
                    'id': node_name, # This is the graph node ID
                    'pos': (x,y)
                })

            # Fetch special places
            cursor.execute("SELECT id, custom_name, x, y FROM special_places")
            special_places = cursor.fetchall()
            for sp_id, custom_name, x, y in special_places:
                locations.append({
                    'display_name': f"{custom_name} (Place)",
                    'search_term': custom_name.lower(), # For case-insensitive search matching
                    'type': 'special_place',
                    'id': sp_id, # This is the special place's own ID
                    'name': custom_name, # Original custom name
                    'pos': (x,y)
                })
            
            # Sort by display name for a nicer dropdown
            locations.sort(key=lambda loc: loc['display_name'])

        except sqlite3.Error as e:
            print(f"SQLite error in get_all_searchable_locations: {e}")
        finally:
            if conn:
                conn.close()
        return locations


