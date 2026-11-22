"""SignalSight – Intelligent Cellular Tower Placement and Coverage Optimization System."""
import streamlit as st

from signalsight import ui, views

st.set_page_config(page_title="SignalSight", page_icon="📡", layout="wide")
ui.inject_css()
views.init_state()

with st.sidebar:
    st.markdown('<div class="ss-brand">📡 SignalSight</div><div class="ss-sub">Tower placement & coverage optimisation</div>',
                unsafe_allow_html=True)
    st.radio("Navigate", views.PAGES, key="nav", label_visibility="collapsed")
    s = st.session_state
    st.divider()
    if "cfg" in s:
        st.markdown(f'<span class="pill ok">✔ {len(s["cfg"]["towers"])} towers analysed</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="pill">no analysis yet</span>', unsafe_allow_html=True)
    if s.get("opt") is not None:
        st.markdown(f'<span class="pill ok">✔ {len(s["opt"].proposed)} sites proposed</span>', unsafe_allow_html=True)
    st.caption("Predictions come from a path-loss model, not field measurements.")

PAGE_FUNCS = {
    views.PAGE_WELCOME: views.page_welcome,
    views.PAGE_CONFIG: views.page_configure,
    views.PAGE_MAP: views.page_map,
    views.PAGE_OPT: views.page_optimizer,
    views.PAGE_REPORT: views.page_report,
}
page = st.session_state["nav"]
# A container whose key changes with the page is re-created on every page change, which is what lets the CSS
# play the slow fade-in (see ui.CSS, ".st-key-page_*") each time a new page opens.
with st.container(key=f"page_{views.PAGES.index(page)}"):
    PAGE_FUNCS[page]()
