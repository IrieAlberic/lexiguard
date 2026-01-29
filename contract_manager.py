import os
import tempfile
import streamlit as st

class ContractManager:
    @staticmethod
    def save_uploaded_file(uploaded_file):
        """Saves an uploaded file to a temporary location."""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                return tmp_file.name
        except Exception as e:
            st.error(f"Error saving file: {e}")
            return None

    @staticmethod
    def cleanup_file(file_path):
        """Removes the temporary file."""
        if os.path.exists(file_path):
            os.unlink(file_path)
