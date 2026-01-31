import streamlit as st
import streamlit.components.v1 as components
import polars as pl
import os

# Module importieren
from src.data_loader import load_graph_data, get_node_list, list_available_files
from src.visualization import render_interactive_network
from src.filters import NetworkFilter

# --- KONFIGURATION ---
DATA_DIR = "data"
GRAPH_LABEL_MAPPING = {
    "graph_a.gexf": "Netzwerk 2023 (Intern)",
    "graph_b.gexf": "Netzwerk 2024 (Extern)",
    # Weitere hier hinzufügen...
}

st.set_page_config(layout="wide", page_title="Netzwerk Dashboard")

# --- HELPER: RESET FUNKTION ---
def reset_filters():
    """
    Setzt alle Filter zurück.
    """
    if "country_selector" in st.session_state:
        del st.session_state["country_selector"]
    
    # NEU: Wir müssen sicherstellen, dass beim Reset wieder "Alle anzeigen" gilt.
    # Checkboxen in Streamlit merken sich ihren Zustand oft basierend auf dem User-Input.
    # Wir können versuchen, den Key zu löschen (falls wir einen vergeben hätten) 
    # oder wir lassen es so, da der Multiselect beim Dateiwechsel eh neu geladen wird.
    
    # Für die neue Logik ist es am saubersten, wenn wir "country_selector" löschen (passiert oben)
    # und die Checkbox manuell resetten, falls wir ihr einen Key geben würden.
    # Da die Checkbox oben keinen 'key' Parameter hat, wird sie beim Rerun
    # auf ihren 'value=True' Default zurückgesetzt, sofern Streamlit sie als "neues Widget" sieht.
    
    if "degree_slider" in st.session_state:
        del st.session_state["degree_slider"]
    if "degree_input" in st.session_state:
        del st.session_state["degree_input"]
    if "node_selector" in st.session_state:
        del st.session_state["node_selector"]

# --- 1. DATEI AUSWAHL (SIDEBAR OBEN) ---
st.sidebar.header("📁 Datensatz")

available_files = list_available_files(DATA_DIR)
if not available_files:
    st.error("Keine .gexf Dateien im 'data' Ordner gefunden!")
    st.stop()

def format_func(filename):
    return GRAPH_LABEL_MAPPING.get(filename, filename.replace(".gexf", ""))

selected_file = st.sidebar.selectbox(
    "Graph auswählen:",
    options=available_files,
    format_func=format_func,
    on_change=reset_filters 
)

file_path = os.path.join(DATA_DIR, selected_file)

# --- 2. DATEN LADEN & VORBEREITEN ---
try:
    G_raw, df_raw, w_degrees = load_graph_data(file_path)
except Exception as e:
    st.error(f"Fehler beim Laden von {selected_file}: {e}")
    st.stop()

# Globale Variable für verfügbare Länder
available_countries = sorted(list(set(df_raw["country"].drop_nulls().to_list())))


# --- 3. FILTER UI (SIDEBAR) ---
st.sidebar.header("Filter")

# A) Country Filter (Direkt im Expander)
# Wir nutzen einen Expander, damit die lange Liste an ausgewählten "Chips"
# standardmäßig versteckt ist und die Sidebar sauber bleibt.
with st.sidebar.expander("Länder Filter", expanded=False):
    
    # 1. Helper Buttons
    col_all, col_none = st.columns(2)
    
    # Button Logik: Manipuliert direkt den Session State des Multiselects
    if col_all.button("Alle auswählen"):
        st.session_state.country_selector = available_countries
        st.rerun()
        
    if col_none.button("Auswahl löschen"):
        st.session_state.country_selector = []
        st.rerun()

    # 2. Der eigentliche Multiselect
    # Wichtig: Wenn 'key' im Session State existiert, ignoriert Streamlit 'default'.
    # Das ist gut, damit unsere Button-Logik funktioniert.
    selected_countries = st.multiselect(
        "Länder:",
        options=available_countries,
        default=available_countries, # Standardmäßig alle ausgewählt beim ersten Laden
        key="country_selector"
    )

# B) Weighted Degree Filter (Synchronisiert)
st.sidebar.markdown("**Min. Interlocks**")

# 1. Maximalwert ermitteln
max_degree = int(df_raw["weighted_degree"].max()) if not df_raw.is_empty() else 10

# 2. Initialisierung der Session State Keys (falls noch nicht vorhanden)
if "degree_slider" not in st.session_state:
    st.session_state.degree_slider = 0
if "degree_input" not in st.session_state:
    st.session_state.degree_input = 0

# 3. Callback Funktionen (Cross-Update)
def update_slider_from_input():
    # Wenn Textfeld geändert wurde -> Slider Key aktualisieren
    # Wir müssen sicherstellen, dass wir nicht über das Maximum gehen
    new_val = st.session_state.degree_input
    if new_val > max_degree:
        new_val = max_degree
    st.session_state.degree_slider = new_val

def update_input_from_slider():
    # Wenn Slider geändert wurde -> Textfeld Key aktualisieren
    st.session_state.degree_input = st.session_state.degree_slider

# 4. Layout & Widgets
col_input, col_slider = st.sidebar.columns([1, 2])

with col_input:
    st.number_input(
        "Wert",
        min_value=0,
        max_value=max_degree,
        key="degree_input",          # Eigener Key
        on_change=update_slider_from_input, # Ruft Callback auf
        label_visibility="collapsed"
    )

with col_slider:
    st.slider(
        "Slider",
        min_value=0,
        max_value=max_degree,
        key="degree_slider",         # Eigener Key
        on_change=update_input_from_slider, # Ruft Callback auf
        label_visibility="collapsed"
    )

# Der Wert für den Filter ist nun egal von welchem Widget (da beide synchron sind)
min_degree = st.session_state.degree_slider

# --- 4. FILTER LOGIK ANWENDEN (Rest bleibt gleich) ---
display_G, df_display = NetworkFilter.apply_filters(
    G_raw, 
    df_raw, 
    selected_countries, 
    min_degree
)

# --- 5. UI RENDERING ---
st.sidebar.markdown("---")
st.sidebar.subheader("Darstellung")
st.sidebar.metric("Knoten", display_G.number_of_nodes())
st.sidebar.metric("Kanten", display_G.number_of_edges())

# NEU: Der Toggle Switch für die Formen
use_shapes = st.sidebar.toggle(
    "Inhaltstyp anzeigen (Formen)", 
    value=False,
    help="Ein: Unterscheidet Knoten nach Denial (Dreieck) und Climate (Quadrat).\nAus: Alle Knoten sind Kreise."
)

col_graph, col_details = st.columns([3, 1])

with col_graph:
    st.subheader(f"Visualization")
    st.text("Drag and drop to explore the network. " \
    "\\Zoom in/out with your mouse wheel / trackpad. " \
    "\\Use the buttons to start/stop the simulation.")
    
    if display_G.number_of_nodes() > 0:
        # WICHTIG: Hier übergeben wir jetzt den Zustand des Switches
        html_content = render_interactive_network(
            display_G, 
            height="700px", 
            use_custom_shapes=use_shapes 
        )
        
        components.html(
            html_content, 
            height=720, 
            scrolling=False
        )
    else:
        st.warning("Alle Knoten wurden ausgefiltert. Bitte Filter anpassen.")


with col_details:
    st.subheader("Details")
    
    all_nodes = get_node_list(df_display)
    
    selected_node_id = st.selectbox(
        "Knoten suchen:", 
        options=all_nodes,
        key="node_selector"
    )

    if selected_node_id:
        node_info = df_display.filter(pl.col("node_id") == selected_node_id)
        if not node_info.is_empty():
            info_dict = node_info.row(0, named=True)
            st.markdown("### Attribute")
            for key, value in info_dict.items():
                if key == "weighted_degree":
                    st.write(f"**Interlocks:** {value:.2f}")
                else:
                    st.write(f"**{key.capitalize()}:** {value}")