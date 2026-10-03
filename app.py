import io
import streamlit as st
import markdown
from xhtml2pdf import pisa
from pipeline import run_research_pipeline

def _md_to_pdf(md_text: str) -> bytes:
    html = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    full_html = f"""
    <html><head><style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; color: #222; }}
        h1, h2, h3 {{ color: #111; margin-top: 1.2em; }}
        ul {{ margin-left: 1.5em; }}
        a {{ color: #0055cc; }}
        code {{ background: #f4f4f4; padding: 2px 4px; font-size: 0.9em; }}
    </style></head><body>{html}</body></html>
    """
    buf = io.BytesIO()
    pisa.CreatePDF(full_html, dest=buf)
    return buf.getvalue()

st.set_page_config(page_title="Multi-Agent Research System", page_icon="🔍", layout="wide")

st.title("🔍 Multi-Agent Research System")
st.caption("Powered by Claude + Tavily | Search → Scrape → Write → Critique")

topic = st.text_input("Enter a research topic", placeholder="e.g. BRICS latest news")

if st.button("Run Research", type="primary", disabled=not topic.strip()):
    with st.status("Running research pipeline...", expanded=True) as status:
        st.write("Step 1: Search agent gathering information...")
        st.write("Step 2: Scrape agent extracting content...")
        st.write("Step 3: Writer drafting the report...")
        st.write("Step 4: Critic reviewing the report...")
        try:
            state = run_research_pipeline(topic)
            status.update(label="Research complete!", state="complete")
        except Exception as e:
            status.update(label="Pipeline failed", state="error")
            st.error(f"Error: {e}")
            st.stop()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📄 Research Report")
        st.markdown(state["report"])

        st.download_button(
            label="Download Report (PDF)",
            data=_md_to_pdf(state["report"]),
            file_name=f"{topic[:50].replace(' ', '_')}_report.pdf",
            mime="application/pdf",
        )

        with st.expander("Search Results"):
            st.text(state["search_results"])

        with st.expander("Scraped Content"):
            st.text(state["scraped_content"])

    with col2:
        st.subheader("🧐 Critic Feedback")
        st.markdown(state["feedback"])
