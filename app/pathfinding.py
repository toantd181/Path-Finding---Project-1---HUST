import sqlite3
import networkx as nx
import os
from PyQt6.QtCore import QPointF, QLineF # Add this import

def point_segment_distance(p: QPointF, a: QPointF, b: QPointF) -> (float, QPointF):
    """
    Calculates the shortest distance from point p to line segment ab.
    Returns: (distance, closest_point_on_segment)
    """
    ab_x = b.x() - a.x()
    ab_y = b.y() - a.y()
    ap_x = p.x() - a.x()
    ap_y = p.y() - a.y()

    len_sq_ab = ab_x * ab_x + ab_y * ab_y
    if abs(len_sq_ab) < 1e-9:
        # a and b are the same point
        dist = QLineF(p, a).length()
        return dist, a

    t = (ap_x * ab_x + ap_y * ab_y) / len_sq_ab
    
    if t < 0.0:
        t = 0.0
        closest_point_on_line = a
    elif t > 1.0:
        t = 1.0
        closest_point_on_line = b
    else:
        closest_point_on_line = QPointF(a.x() + t * ab_x, a.y() + t * ab_y)
        
    dist = QLineF(p, closest_point_on_line).length()
    return dist, closest_point_on_line

class Pathfinding:
    def __init__(self, graph_db_path):
        self.graph = nx.DiGraph()
        self.db_path = graph_db_path
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found: {self.db_path}")
        self.load_graph_from_db(self.db_path)
        self._temp_changes = [] # <<< ADD THIS LINE

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

            return ((pos_u[0] - pos_v[0])**2 + (pos_u[1] - pos_v[1])**2)**0.5 / 100

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

    # --- Add the new methods below ---

    def find_edges_near_line(self, line_p1: QPointF, line_p2: QPointF, threshold: float):
        """
        Finds graph edges whose midpoints are within a given threshold distance
        from the line segment defined by line_p1 and line_p2.
        """
        affected_edges = []
        if not self.graph:
            return affected_edges

        for u, v in self.graph.edges():
            try:
                pos_u_tuple = self.graph.nodes[u]['pos']
                pos_v_tuple = self.graph.nodes[v]['pos']

                # Midpoint of the graph edge
                edge_mid_x = (pos_u_tuple[0] + pos_v_tuple[0]) / 2
                edge_mid_y = (pos_u_tuple[1] + pos_v_tuple[1]) / 2
                edge_midpoint = QPointF(edge_mid_x, edge_mid_y)

                # Calculate distance from edge_midpoint to the line_p1-line_p2 segment
                # (Using logic similar to point_segment_distance from main_window.py)
                
                # Vector from line_p1 to line_p2
                line_vec_x = line_p2.x() - line_p1.x()
                line_vec_y = line_p2.y() - line_p1.y()

                # Vector from line_p1 to edge_midpoint
                point_vec_x = edge_midpoint.x() - line_p1.x()
                point_vec_y = edge_midpoint.y() - line_p1.y()

                len_sq_line = line_vec_x * line_vec_x + line_vec_y * line_vec_y
                
                dist = float('inf')
                if abs(len_sq_line) < 1e-9: # line_p1 and line_p2 are effectively the same point
                    dist = QLineF(edge_midpoint, line_p1).length()
                else:
                    # Project point_vec onto line_vec
                    t = (point_vec_x * line_vec_x + point_vec_y * line_vec_y) / len_sq_line
                    
                    closest_point_on_line = QPointF()
                    if t < 0.0: # Projection is beyond line_p1
                        closest_point_on_line = line_p1
                    elif t > 1.0: # Projection is beyond line_p2
                        closest_point_on_line = line_p2
                    else: # Projection is on the segment
                        closest_point_on_line = QPointF(line_p1.x() + t * line_vec_x, 
                                                        line_p1.y() + t * line_vec_y)
                    dist = QLineF(edge_midpoint, closest_point_on_line).length()

                if dist < threshold:
                    affected_edges.append((u, v))
            except KeyError:
                # This can happen if a node in an edge doesn't have 'pos' data.
                # load_graph_from_db should prevent this, but good to be safe.
                # print(f"Warning: Position data missing for edge ({u}-{v}) in find_edges_near_line.")
                continue
            except Exception as e:
                # print(f"Warning: Error processing edge ({u}-{v}) in find_edges_near_line: {e}")
                continue
            
        return affected_edges

    def modify_edge_weight(self, u, v, add_weight=None, set_weight=None):
        """Modifies the weight of an edge (u,v) in the graph."""
        if not self.graph.has_edge(u, v):
            # print(f"Warning: Edge ({u}-{v}) not found in graph. Cannot modify weight.")
            return

        if add_weight is not None:
            current_weight = self.graph[u][v].get('weight', 0.0) # Default to 0.0 if no weight
            # Ensure current_weight is a number
            if not isinstance(current_weight, (int, float)):
                current_weight = 0.0
            self.graph[u][v]['weight'] = current_weight + add_weight
            # print(f"DEBUG Pathfinding: Edge ({u}-{v}) weight changed from {current_weight:.2f} to {self.graph[u][v]['weight']:.2f} (added {add_weight:.2f})")
        elif set_weight is not None:
            # old_weight = self.graph[u][v].get('weight', "N/A")
            self.graph[u][v]['weight'] = set_weight

    def add_virtual_node(self, click_x: float, click_y: float, preferred_id: str) -> (str, tuple):
        """
        Finds the nearest edge, splits it, and adds a temporary virtual node.
        Returns: (new_node_id, (actual_x, actual_y))
        """
        
        click_point = QPointF(click_x, click_y)
        
        # 1. Find the nearest edge in the graph
        min_dist = float('inf')
        best_edge = None
        closest_point_on_edge = None
        
        for u, v in self.graph.edges():
            pos_u_tuple = self.graph.nodes[u].get('pos')
            pos_v_tuple = self.graph.nodes[v].get('pos')

            if not pos_u_tuple or not pos_v_tuple:
                continue # Skip edges with missing node data

            pos_u = QPointF(*pos_u_tuple)
            pos_v = QPointF(*pos_v_tuple)
            
            dist, closest_point = point_segment_distance(click_point, pos_u, pos_v)
            
            if dist < min_dist:
                min_dist = dist
                best_edge = (u, v)
                closest_point_on_edge = closest_point

        # 2. Fallback: If no edge is found (e.g., empty graph)
        if best_edge is None:
            print("Warning: No best edge found. Finding nearest node as fallback.")
            nearest_node_id = None
            min_node_dist = float('inf')
            
            for node_id, data in self.graph.nodes(data=True):
                pos_tuple = data.get('pos')
                if not pos_tuple:
                    continue
                
                node_dist = QLineF(click_point, QPointF(*pos_tuple)).length()
                if node_dist < min_node_dist:
                    min_node_dist = node_dist
                    nearest_node_id = node_id
            
            if nearest_node_id:
                new_node_id = preferred_id
                actual_pos = (click_x, click_y) # Use exact click pos
                
                self.graph.add_node(new_node_id, pos=actual_pos)
                weight = min_node_dist # Weight = distance
                
                # Add edges in both directions for simplicity
                self.graph.add_edge(new_node_id, nearest_node_id, weight=weight)
                self.graph.add_edge(nearest_node_id, new_node_id, weight=weight)
                
                self._temp_changes.append(('node', new_node_id))
                self._temp_changes.append(('edge', (new_node_id, nearest_node_id)))
                self._temp_changes.append(('edge', (nearest_node_id, new_node_id)))
                
                return new_node_id, actual_pos
            else:
                return None, None # Complete failure

        # 3. We found a best edge. Split it.
        u, v = best_edge
        new_node_id = preferred_id
        actual_pos = (closest_point_on_edge.x(), closest_point_on_edge.y())
        
        # 4. Store original edge data, remove it, add new node
        original_edge_data = self.graph.get_edge_data(u, v).copy()
        self._temp_changes.append(('edge_split', (u, v, original_edge_data)))
        
        self.graph.remove_edge(u, v)
        self.graph.add_node(new_node_id, pos=actual_pos)
        
        # 5. Calculate new weights (proportional to distance)
        original_weight = original_edge_data.get('weight', 0)
        pos_u = QPointF(*self.graph.nodes[u]['pos'])
        pos_v = QPointF(*self.graph.nodes[v]['pos'])
        
        dist_u_v = QLineF(pos_u, pos_v).length()
        dist_u_new = QLineF(pos_u, closest_point_on_edge).length()
        dist_new_v = QLineF(closest_point_on_edge, pos_v).length()
        
        weight_u_new = 0
        weight_new_v = 0
        
        if abs(dist_u_v) > 1e-9:
            weight_u_new = original_weight * (dist_u_new / dist_u_v)
            weight_new_v = original_weight * (dist_new_v / dist_u_v)
        
        # 6. Add the two new split edges
        self.graph.add_edge(u, new_node_id, weight=weight_u_new)
        self.graph.add_edge(new_node_id, v, weight=weight_new_v)
        
        # 7. Store changes for cleanup
        self._temp_changes.append(('node', new_node_id))
        self._temp_changes.append(('edge', (u, new_node_id)))
        self._temp_changes.append(('edge', (new_node_id, v)))
        
        return new_node_id, actual_pos

    def remove_virtual_nodes(self):
        """
        Restores the graph to its original state by undoing temp changes.
        """
        if not self._temp_changes:
            return
            
        print(f"Cleaning up {len(self._temp_changes)} temporary graph changes.")
        
        # Iterate in reverse to re-add edges before removing nodes
        for change_type, data in reversed(self._temp_changes):
            try:
                if change_type == 'node':
                    # data is node_id
                    if self.graph.has_node(data):
                        self.graph.remove_node(data)
                
                elif change_type == 'edge':
                    # data is (u, v)
                    if self.graph.has_edge(*data):
                        self.graph.remove_edge(*data)
                
                elif change_type == 'edge_split':
                    # data is (u, v, original_edge_data)
                    u, v, original_data = data
                    # Add original edge back
                    if not self.graph.has_edge(u, v):
                        self.graph.add_edge(u, v, **original_data)
            except Exception as e:
                print(f"Error during graph cleanup: {e}")

        # Clear the changes list
        self._temp_changes = []


