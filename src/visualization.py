import networkx as nx
from pyvis.network import Network
import tempfile
import copy

def _prepare_visual_attributes(G_original, use_custom_shapes=False):
    """
    Prepares the graph visual attributes.
    """
    G_vis = copy.deepcopy(G_original)

    # Helper to detect boolean values safely
    def is_true(value):
        return str(value).lower() in ['true', '1', 'yes']

    weighted_degrees = dict(G_vis.degree(weight='weight'))
    
    for node_id, attributes in G_vis.nodes(data=True):
        w_degree = weighted_degrees.get(node_id, 1)
        
        # --- NODE SHAPE LOGIC ---
        node_shape = "dot" 

        if use_custom_shapes:
            has_denial = attributes.get("has_denial_content", False)
            has_climate = attributes.get("has_climate_content", False)

            if is_true(has_denial):
                node_shape = "triangle" 
            elif is_true(has_climate):
                node_shape = "square"    

        attributes['shape'] = node_shape

        # --- VISUAL STYLING ---
        attributes['value'] = w_degree 
        
        # Tooltip content
        type_info = ""
        if use_custom_shapes:
            if node_shape == "triangle": type_info = "\nType: Denial Content"
            elif node_shape == "square": type_info = "\nType: Climate Content"
        
        attributes['title'] = f"Think Tank: {node_id}{type_info}\nInterlocks: {w_degree:.2f}"
        
        attributes['color'] = {
            'background': '#D3D3D3', 
            'border': '#505050',
            'highlight': {
                'background': '#A9A9A9',
                'border': '#000000'
            }
        }
        attributes['borderWidth'] = 2
        attributes['font'] = {'color': 'black', 'face': 'arial', 'strokeWidth': 2, 'strokeColor': '#ffffff'}

    # --- EDGE STYLING ---
    for u, v, attributes in G_vis.edges(data=True):
        weight = attributes.get('weight', 1.0)
        attributes['width'] = weight * 2.5 
        attributes['color'] = '#000000'
        # UPDATED TOOLTIP
        attributes['title'] = f"Edge - Number of Interlocks: {weight}"

    return G_vis

def render_interactive_network(G, height="600px", width="100%", use_custom_shapes=False):
    """
    Renders the Pyvis graph with custom controls.
    """
    if len(G.nodes) == 0:
        return "<div>Empty Graph</div>"

    G_vis = _prepare_visual_attributes(G, use_custom_shapes=use_custom_shapes)

    nt = Network(height=height, width=width, notebook=False)
    nt.from_nx(G_vis)
    
    options = """
    {
      "nodes": {
        "shape": "dot",
        "font": { "face": "Tahoma", "color": "black", "strokeWidth": 2, "strokeColor": "#ffffff" },
        "scaling": {
            "min": 10, "max": 30,
            "label": { "enabled": true, "min": 12, "max": 24, "drawThreshold": 5 }
        },
        "shadow": { "enabled": true }
      },
      "interaction": {
          "hover": true,
          "navigationButtons": true,
          "keyboard": true
      },
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "centralGravity": 0.01,
          "springLength": 100,
          "springConstant": 0.08,
          "damping": 0.9, 
          "avoidOverlap": 0.5
        },
        "minVelocity": 0.75,
        "solver": "forceAtlas2Based",
        "stabilization": { 
            "enabled": true, 
            "iterations": 500,
            "updateInterval": 50
        }
      }
    }
    """
    nt.set_options(options)
    
    try:
        tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        nt.save_graph(tmpfile.name)
        
        with open(tmpfile.name, 'r', encoding='utf-8') as f:
            html_string = f.read()
            
        # --- CUSTOM CONTROLS INJECTION ---
        custom_controls = """
        <div style="
            position: absolute; 
            bottom: 20px; 
            left: 50%; 
            transform: translateX(-50%); 
            z-index: 9999; 
            display: flex; 
            flex-direction: column; 
            align-items: center; 
            gap: 5px; 
            background: rgba(255,255,255,0.9); 
            padding: 10px; 
            border-radius: 8px; 
            border: 1px solid #ccc;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            font-family: sans-serif;
        ">
            <span style="font-size: 12px; font-weight: bold; color: #333; letter-spacing: 0.5px;">
                CONTROL SIMULATION
            </span>
            <div style="display: flex; gap: 10px;">
                <button onclick="network.startSimulation();" style="cursor: pointer; padding: 6px 12px; background: #00cc66; color: white; border: none; border-radius: 4px; font-weight: bold; font-size: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                    ▶️ Start
                </button>
                <button onclick="network.stopSimulation();" style="cursor: pointer; padding: 6px 12px; background: #ff4b4b; color: white; border: none; border-radius: 4px; font-weight: bold; font-size: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                    🛑 Stop
                </button>
            </div>
        </div>
        
        <script>
            setTimeout(function() {
                network.stopSimulation();
                console.log("Simulation auto-stopped.");
            }, 15000); 
        </script>
        """
        
        html_string = html_string.replace('</body>', custom_controls + '</body>')
        
        return html_string
        
    except Exception as e:
        return f"<div>Error generating graph: {e}</div>"