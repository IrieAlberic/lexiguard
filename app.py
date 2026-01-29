import streamlit as st
import os
from utils import init_env
from contract_manager import ContractManager

# Page Config
st.set_page_config(page_title="LexiGuard 3.0", layout="wide")

# Load variables
init_env()

# Sidebar
with st.sidebar:
    st.header("LexiGuard")
    st.markdown("AI Contract Analysis Workbench")
    
    st.divider()
    
    st.subheader("Configuration")
    
    provider = st.selectbox("AI Provider", ["OpenAI", "Google Gemini", "OpenRouter"])
    
    api_key_placeholder = "sk-..."
    if provider == "Google Gemini":
        api_key_placeholder = "AIza..."
    elif provider == "OpenRouter":
        api_key_placeholder = "sk-or-..."
        
    api_key = st.text_input(f"{provider} API Key", type="password", help=f"Enter your {provider} API Key", placeholder=api_key_placeholder)
    
    models = {
        "OpenAI": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        "Google Gemini": ["gemini-pro", "gemini-1.5-pro", "gemini-1.5-flash"],
        "OpenRouter": ["openai/gpt-4o", "anthropic/claude-3-sonnet", "google/gemini-2.0-flash-exp"]
    }
    
    model_name = st.selectbox("Model", models.get(provider, []))
    
    st.divider()
    
    st.subheader("Document Upload")
    uploaded_file = st.file_uploader("Upload Contract (PDF)", type="pdf")

# Main Content
st.title("Contract Analysis Dashboard")

if "rag_engine" not in st.session_state:
    st.session_state.rag_engine = None

if not uploaded_file:
    st.info("Please upload a PDF contract to begin analysis.")
else:
    # If config changes, update engine
    if "rag_engine" in st.session_state and st.session_state.rag_engine:
        st.session_state.rag_engine.configure(provider, api_key, model_name)

    # Save uploaded file temporarily
    if "current_file" not in st.session_state or st.session_state.current_file != uploaded_file.name:
        if not api_key:
             st.warning("Please enter an API Key to ingest.")
        else:
            with st.spinner("Ingesting document..."):
                tmp_path = ContractManager.save_uploaded_file(uploaded_file)
                
                if tmp_path:
                    # Initialize Engine
                    from rag_engine import RAGEngine
                    # Only create new if not exists
                    if not st.session_state.rag_engine:
                        st.session_state.rag_engine = RAGEngine()
                    
                    engine = st.session_state.rag_engine
                    engine.configure(provider, api_key, model_name)
                    
                    try:
                        count = engine.ingest_pdf(tmp_path)
                        st.session_state.current_file = uploaded_file.name
                        st.toast(f"Indexed {count} text chunks!")
                    except Exception as e:
                        st.error(f"Error ingesting file: {str(e)}")
                    finally:
                        ContractManager.cleanup_file(tmp_path)

    st.success(f"Active Document: {uploaded_file.name}")
    
    # Tabs
    tab1, tab2 = st.tabs(["Chat Assistant", "Risk Analysis"])
    
    with tab1:
        st.subheader("Chat with your Contract")
        
        # Chat History
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
        if prompt := st.chat_input("Ask about the contract..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
                
            with st.chat_message("assistant"):
                if st.session_state.rag_engine:
                    response = st.session_state.rag_engine.chat(prompt)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                else:
                    st.error("Engine not initialized.")
        
    with tab2:
        st.subheader("Risk & Clause Extraction")
        if st.button("Analyze Risks"):
            if st.session_state.rag_engine:
                with st.spinner("Analyzing risks..."):
                    risks = st.session_state.rag_engine.chat("Identify high-risk clauses in this contract, specifically Indemnification, Termination, and Liability Caps. Format as a markdown list.")
                    st.markdown(risks)

