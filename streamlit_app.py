import streamlit as st
import streamlit.components.v1 as components
import polars as pl
import os
import networkx as nx # NEU: Für die Ego-Graph Berechnung benötigt

# Import modules
from src.data_loader import load_graph_data, get_node_list, list_available_files
from src.visualization import render_interactive_network
from src.filters import NetworkFilter

# --- CONFIGURATION ---
DATA_DIR = "data"
# Please update the labels to match your specific filenames
GRAPH_LABEL_MAPPING = {
    "global_table_nonpartite.gexf": "Global Network",
    "transcontinental_table_nonpartite.gexf": "Transcontinental Network",
    "intra_w_national_oceania.gexf": "Intraregional: Oceania & Asia",
    "intra_w_national_africa.gexf": "Intraregional: Africa",
    "intra_w_national_na.gexf": "Intraregional: North America",
    "intra_w_national_la.gexf": "Intraregional: Latin America",
    "intra_w_national_eu.gexf": "Intraregional: Europe",
    "intra_wo_national_oceania.gexf": "Intraregional (w/o national Interlocks): Oceania & Asia",
    "intra_wo_national_africa.gexf": "Intraregional (w/o national Interlocks): Africa & MENA",
    "intra_wo_national_na.gexf": "Intraregional (w/o national Interlocks): North America",
    "intra_wo_national_la.gexf": "Intraregional (w/o national Interlocks): Latin America",
    "intra_wo_national_eu.gexf": "Intraregional (w/o national Interlocks): Europe"
}

# 1. Update Page Config
st.set_page_config(layout="wide", page_title="Atlas Network Visualizer")

# 2. Add Main Website Title
st.title("Atlas Network Visualizer")

# --- HELPER: RESET FUNCTION ---
def reset_filters():
    """
    Resets all filters to their default states.
    """
    if "country_selector" in st.session_state:
        del st.session_state["country_selector"]
    if "degree_slider" in st.session_state:
        del st.session_state["degree_slider"]
    if "degree_input" in st.session_state:
        del st.session_state["degree_input"]
    if "node_selector" in st.session_state:
        del st.session_state["node_selector"]

# ==========================================
# 1. GLOBAL SIDEBAR (Top)
# ==========================================
st.sidebar.header("Dataset")

available_files = list_available_files(DATA_DIR)
if not available_files:
    st.error("No .gexf files found in 'data' directory!")
    st.stop()

def format_func(filename):
    return GRAPH_LABEL_MAPPING.get(filename, filename.replace(".gexf", ""))

selected_file = st.sidebar.selectbox(
    "Select Network:",
    options=available_files,
    format_func=format_func,
    on_change=reset_filters 
)

file_path = os.path.join(DATA_DIR, selected_file)

# --- LOAD DATA ---
try:
    G_raw, df_raw, w_degrees = load_graph_data(file_path)
except Exception as e:
    st.error(f"Error loading {selected_file}: {e}")
    st.stop()

available_countries = sorted(list(set(df_raw["country"].drop_nulls().to_list())))

st.sidebar.markdown("---")

# --- VIEW SETTINGS (Above Tabs) ---
st.sidebar.subheader("View Settings")

use_shapes = st.sidebar.toggle(
    "Toggle Node Shape", 
    value=False,
    help="Draw the nodes in different shapes depending on their climate content."
)

# Legend (Global)
if use_shapes:
    st.sidebar.caption("Legend:")
    
    # DOT
    st.sidebar.markdown(
        """
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <span style="display: inline-block; width: 12px; height: 12px; background-color: #D3D3D3; border: 2px solid #505050; border-radius: 50%; margin-right: 8px;"></span>
            <span style="font-size: 14px;">No Climate Content</span>
        </div>
        """, unsafe_allow_html=True
    )
    # SQUARE
    st.sidebar.markdown(
        """
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <span style="display: inline-block; width: 12px; height: 12px; background-color: #D3D3D3; border: 2px solid #505050; margin-right: 8px;"></span>
            <span style="font-size: 14px;">Climate Content (no Denial)</span>
        </div>
        """, unsafe_allow_html=True
    )
    # TRIANGLE
    st.sidebar.markdown(
        """
        <div style="display: flex; align-items: center;">
            <svg width="14" height="14" style="margin-right: 6px;">
                <polygon points="7,1 13,13 1,13" style="fill:#D3D3D3;stroke:#505050;stroke-width:2" />
            </svg>
            <span style="font-size: 14px;">Climate Denial Content</span>
        </div>
        """, unsafe_allow_html=True
    )

st.sidebar.markdown("---")

# ==========================================
# 2. SIDEBAR TABS (Below)
# ==========================================
tab_filter, tab_details = st.sidebar.tabs(["Filter", "Inspect"])

# --- TAB 1: FILTER INPUTS ---
with tab_filter:
    st.header("Filter Options")
    
    # A) Country Filter
    with st.expander("Country Filter", expanded=False):
        col_all, col_none = st.columns(2)
        if col_all.button("Select All"):
            st.session_state.country_selector = available_countries
            st.rerun()
        if col_none.button("Clear Selection"):
            st.session_state.country_selector = []
            st.rerun()

        selected_countries = st.multiselect(
            "Countries:",
            options=available_countries,
            default=available_countries,
            key="country_selector"
        )

    # B) Weighted Degree Filter
    st.markdown("**Min. Interlocks**")

    max_degree = int(df_raw["weighted_degree"].max()) if not df_raw.is_empty() else 10

    if "degree_slider" not in st.session_state:
        st.session_state.degree_slider = 0
    if "degree_input" not in st.session_state:
        st.session_state.degree_input = 0

    def update_slider_from_input():
        new_val = st.session_state.degree_input
        if new_val > max_degree: new_val = max_degree
        st.session_state.degree_slider = new_val

    def update_input_from_slider():
        st.session_state.degree_input = st.session_state.degree_slider

    col_input, col_slider = st.columns([1, 2])
    with col_input:
        st.number_input("Value", min_value=0, max_value=max_degree, key="degree_input", on_change=update_slider_from_input, label_visibility="collapsed")
    with col_slider:
        st.slider("Slider", min_value=0, max_value=max_degree, key="degree_slider", on_change=update_input_from_slider, label_visibility="collapsed")

    min_degree = st.session_state.degree_slider


# --- APPLY LOGIC (Step 1: Global Filters) ---
display_G, df_display = NetworkFilter.apply_filters(
    G_raw, df_raw, selected_countries, min_degree
)


# --- TAB 2: INSPECT (EGO GRAPH LOGIC) ---
# Wir bearbeiten Tab 2 VOR dem Rendering, da die Auswahl hier 
# den Graphen (display_G) verändern kann.
with tab_details:
    st.header("Think Tank Details")
    
    # 1. Reset Button Logic
    if st.button("Reset View (Show Full Graph)", use_container_width=True):
        st.session_state.node_selector = None
        st.rerun()

    # 2. Node Selector
    # Wir nehmen alle Knoten aus dem (gefilterten) DF für die Liste
    all_nodes = get_node_list(df_display)
    
    selected_node_id = st.selectbox(
        "Inspect Think Tank:", 
        options=all_nodes,
        index=None,               # Standard: Nichts ausgewählt
        placeholder="Select to inspect...",
        key="node_selector"
    )

    if selected_node_id:
        st.divider()
        
        # --- EGO GRAPH LOGIC ---
        # Wenn ein Knoten ausgewählt ist, überschreiben wir display_G 
        # mit einem Teilgraphen (Knoten + direkte Nachbarn).
        # radius=1 bedeutet: Nur direkte Nachbarn.
        try:
            # Wir berechnen den Ego Graph basierend auf dem aktuell gefilterten Graphen
            if selected_node_id in display_G:
                display_G = nx.ego_graph(display_G, selected_node_id, radius=1)
                st.success(f"Showing network for: {selected_node_id}")
            else:
                st.warning("Selected node is currently hidden by filters.")
        except Exception as e:
            st.error(f"Error creating ego graph: {e}")

        # --- DETAILS DISPLAY ---
        node_info = df_display.filter(pl.col("node_id") == selected_node_id)
        
        if not node_info.is_empty():
            info_dict = node_info.row(0, named=True)
            st.markdown(f"### {selected_node_id}")
            for key, value in info_dict.items():
                if key == "weighted_degree":
                     st.write(f"**Interlocks:** {value:.2f}")
                elif key != "node_id":
                     # Bereinigung von _ und Capitalize für schönere Anzeige
                     clean_key = key.replace("_", " ").capitalize()
                     st.write(f"**{clean_key}:** {value}")
    else:
        st.info("Select a Think Tank above to isolate its network and see details.")


# --- TAB 1: FILTER OUTPUTS (Metrics) ---
# Die Metriken zeigen wir erst JETZT an, damit sie auf den (potenziell reduzierten)
# Graphen reagieren. Wenn man einen Knoten inspiziert, sieht man also:
# "Think Tanks: 5" (1 Fokus + 4 Nachbarn).
with tab_filter:
    st.markdown("---")
    st.caption("Result (Current View):")
    col_metric1, col_metric2 = st.columns(2)
    col_metric1.metric("Think Tanks", display_G.number_of_nodes())


# ==========================================
# 3. MAIN AREA (Visualization)
# ==========================================
st.subheader("Network Visualization")

# Je nachdem ob Ego-Modus oder nicht, ändert sich der Titel dynamisch
if selected_node_id:
    st.caption(f"Inspect View: {selected_node_id} and connected think tanks")

# --- NAVIGATION GUIDE (NEU) ---
with st.expander("How to Navigate the Graph", expanded=True):
    st.markdown(
        """
        <div style="font-size: 14px; color: #fff;">
        <ul style="margin-bottom: 0;">
            <li><b>Move:</b> Click and drag an empty space, use your keyboard <b>arrow keys</b>, or the <b>arrow buttons</b> on the bottom panel.</li>
            <li><b>Zoom:</b> Use your mouse wheel / trackpad, or the <b>(+)</b> and <b>(-)</b> buttons.</li>
            <li><b>Reset View:</b> Click the <b>target icon</b> to fit the graph to the screen.</li>
            <li><b>Simulation Control:</b> If the network is jittering or moving too much, click <b style="color: #ff4b4b;">Stop</b> to freeze the nodes. Click <b style="color: #00cc66;">Start</b> to resume the physics simulation.</li>
        </ul>
        </div>
        """, 
        unsafe_allow_html=True
    )

if display_G.number_of_nodes() > 0:
    html_content = render_interactive_network(
        display_G, 
        height="750px", 
        use_custom_shapes=use_shapes
    )
    
    components.html(html_content, height=770, scrolling=False)
else:
    st.warning("All Think Tanks have been filtered out.")