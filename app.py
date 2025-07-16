# ui/streamlit_app.py

import streamlit as st
from agent.github_agent import build_agent

st.set_page_config(page_title="GitHub Repo Analyzer", layout="centered")
st.title("🔍 GitHub Repo Analyzer with MCP")

query = st.text_input("Ask something about your GitHub repository:")

if query:
    with st.spinner("Thinking..."):
        agent = build_agent()
        response = agent.run(query)
        st.success("Response:")
        st.write(response)
