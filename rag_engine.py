import os
import tempfile
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

class RAGEngine:
    def __init__(self, persist_directory="./chroma_db"):
        self.persist_directory = persist_directory
        self.vectorstore = None
        self.retriever = None
        self.provider = "OpenAI"
        self.api_key = None
        self.model_name = "gpt-4o-mini"
        
    def configure(self, provider, api_key, model_name):
        """Updates the configuration."""
        self.provider = provider
        self.api_key = api_key
        self.model_name = model_name
        
    def _get_embeddings(self):
        """Returns the appropriate embedding model based on provider."""
        if self.provider == "Google Gemini":
             if not self.api_key:
                 raise ValueError("Google API Key required")
             return GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=self.api_key)
        else:
             # Default to OpenAI for OpenAI and OpenRouter (unless OpenRouter has specific ones, but standard OpenAI works better usually)
             if not self.api_key:
                 raise ValueError("OpenAI API Key required")
             # Note: For OpenRouter, we might need a different base_url, but for embeddings usually people use OpenAI directly.
             # Simplification: We assume if using OpenRouter, user might still provide OpenAI key OR we use OpenRouter for embeddings if compatible.
             # For this simple implementation, we force OpenAI embeddings for non-Gemini.
             return OpenAIEmbeddings(openai_api_key=self.api_key)

    def ingest_pdf(self, file_path):
        """Loads a PDF, splits it, and indexing it into ChromaDB."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        # 1. Load
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        
        # 2. Split
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)
        
        # 3. Embed & Store
        embeddings = self._get_embeddings()
        
        # We must use a unique directory for different providers/models to avoid dimension mismatch
        persist_dir = f"{self.persist_directory}_{self.provider.replace(' ', '_')}"
        
        self.vectorstore = Chroma.from_documents(
            documents=splits, 
            embedding=embeddings, 
            persist_directory=persist_dir
        )
        self.retriever = self.vectorstore.as_retriever()
        
        return len(splits)

    def chat(self, question):
        """Answers a question using the RAG chain."""
        if not self.retriever:
            return "Please ingest a document first."
            
        if self.provider == "Google Gemini":
            llm = ChatGoogleGenerativeAI(model=self.model_name, google_api_key=self.api_key, temperature=0)
        elif self.provider == "OpenRouter":
             llm = ChatOpenAI(
                 model_name=self.model_name,
                 openai_api_key=self.api_key,
                 openai_api_base="https://openrouter.ai/api/v1",
                 temperature=0
             )
        else: # OpenAI
             llm = ChatOpenAI(model_name=self.model_name, openai_api_key=self.api_key, temperature=0)
        
        template = """Answer the question based only on the following context:
        {context}
        
        Question: {question}
        """
        prompt = ChatPromptTemplate.from_template(template)
        
        def format_docs(docs):
            return "\n\n".join([d.page_content for d in docs])
            
        rag_chain = (
            {"context": self.retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
        
        return rag_chain.invoke(question)

    def extract_risk_analysis(self):
        """Extracts structured risk data (faster and more precise than chat)."""
        if not self.retriever:
            return "Please ingest a document first."
            
        # Select LLM
        if self.provider == "Google Gemini":
            llm = ChatGoogleGenerativeAI(model=self.model_name, google_api_key=self.api_key, temperature=0)
        elif self.provider == "OpenRouter":
             llm = ChatOpenAI(
                 model_name=self.model_name,
                 openai_api_key=self.api_key,
                 openai_api_base="https://openrouter.ai/api/v1",
                 temperature=0
             )
        else:
             llm = ChatOpenAI(model_name=self.model_name, openai_api_key=self.api_key, temperature=0, model_kwargs={"response_format": {"type": "json_object"}})
        
        # Specialized Prompt for Extraction
        template = """You are a legal AI auditor. Your job is to extract risk metadata from the contract context below.
        Return a valid JSON object with exactly these keys: "indemnification", "termination", "liability_cap".
        For each key, provide a brief summary of the clause and a "risk_level" (Low/Medium/High).
        
        Context:
        {context}
        
        JSON Output:
        """
        
        prompt = ChatPromptTemplate.from_template(template)
        
        # Chain
        def format_docs(docs):
            return "\n\n".join([d.page_content for d in docs])
            
        extraction_chain = (
            {"context": self.retriever | format_docs}
            | prompt
            | llm
            | StrOutputParser()
        )
        
        return extraction_chain.invoke({})
