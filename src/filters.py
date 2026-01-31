import networkx as nx
import polars as pl

class NetworkFilter:
    """
    Kapselt die Filterlogik für Länder und Knotengrad.
    """

    @staticmethod
    def apply_filters(G: nx.Graph, df: pl.DataFrame, selected_countries: list, min_degree: int):
        """
        Wendet Filter in Reihenfolge an:
        1. Country Filter
        2. Weighted Degree Filter (auf das Ergebnis von 1)
        
        Returns:
            tuple: (filtered_graph, filtered_dataframe)
        """
        
        # --- 1. Filter: Country ---
        # Wenn die Liste leer ist, zeigen wir nichts an (oder alles? User choice. Hier: nichts wenn nichts gewählt)
        if not selected_countries:
            return nx.Graph(), df.clear()
            
        # Polars Filter (extrem schnell)
        # Wir filtern nach Ländern UND nach Mindestgrad gleichzeitig
        filtered_df = df.filter(
            (pl.col("country").is_in(selected_countries)) &
            (pl.col("weighted_degree") >= min_degree)
        )
        
        # --- 2. Graph Update ---
        # Wir holen uns die IDs der übrig gebliebenen Knoten
        nodes_to_keep = filtered_df["node_id"].to_list()
        
        if not nodes_to_keep:
            return nx.Graph(), filtered_df
            
        # Subgraphen erstellen
        filtered_G = G.subgraph(nodes_to_keep)
        
        return filtered_G, filtered_df