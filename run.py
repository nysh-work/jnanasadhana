import streamlit as st
import os
from streamlit.web.server.server import Server
from streamlit.web.server import Server as StreamlitServer
import sys
import streamlit.web.cli as stcli
import sys
import os
from app_v2 import main

# Add static file serving
@st.cache_resource
def setup_static_files():
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(script_dir, "static")
    
    # Register the static directory with Streamlit
    if hasattr(st, "_components") and hasattr(st._components, "declare_component"):
        st._components.declare_component(
            "static_files",
            path=static_dir
        )
    return True

if __name__ == "__main__":
    
    # Run the app
    main()