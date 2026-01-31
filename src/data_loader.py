import streamlit as st
import networkx as nx
import polars as pl
import os

def list_available_files(directory="data"):
    """Listet alle .gexf Dateien im Verzeichnis auf."""
    if not os.path.exists(directory):
        return []
    return [f for f in os.listdir(directory) if f.endswith(".gexf")]

@st.cache_resource
def load_graph_data(file_path: str):
    """
    Lädt GEXF, berechnet Weighted Degree und gibt Graph + Polars DF zurück.
    """
    G = nx.read_gexf(file_path)
    
    # --- Performance Optimierung: Weighted Degree vorbrechnen ---
    # Wir berechnen das hier EINMAL für den ganzen Graphen.
    # Das ist effizienter als es bei jedem Slider-Move neu zu tun.
    weighted_degrees = dict(G.degree(weight='weight'))
    
    data = []
    for node_id, attributes in G.nodes(data=True):
        # Wir reichern die Attribute an
        attributes['node_id'] = node_id
        # Falls kein Country gesetzt ist, setzen wir "Unknown"
        attributes['country'] = attributes.get('country', 'Unknown')
        # Weighted Degree hinzufügen
        attributes['weighted_degree'] = weighted_degrees.get(node_id, 0)
        
        data.append(attributes)
        
    if data:
        df_nodes = pl.DataFrame(data)
    else:
        df_nodes = pl.DataFrame({"node_id": [], "country": [], "weighted_degree": []})
        
    return G, df_nodes, weighted_degrees

def get_node_list(df: pl.DataFrame):
    return df["node_id"].to_list()