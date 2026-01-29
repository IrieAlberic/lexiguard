@echo off
echo Setting up LexiGuard 3.0 Environment...
python -m venv venv
call venv\Scripts\activate.bat
pip install streamlit langchain langchain-community langchain-openai chromadb pypdf python-dotenv
echo Environment Setup Complete.
