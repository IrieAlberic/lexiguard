import os
from dotenv import load_dotenv

def init_env():
    """Load environment variables."""
    load_dotenv()
    
def get_api_key():
    """Retrieve API key from env or return None."""
    return os.getenv("OPENAI_API_KEY")
