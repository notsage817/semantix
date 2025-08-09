import streamlit as st
import requests
import json
import os
from typing import Dict, List, Any

# Page configuration
st.set_page_config(
    page_title="Semantix",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for styling
st.markdown("""
<style>
.main-title {
    text-align: center;
    font-size: 2.5rem;
    font-weight: bold;
    margin-bottom: 0.5rem;
}
.subtitle {
    text-align: center;
    font-size: 1.2rem;
    color: #666;
    margin-bottom: 2rem;
}
.chat-container {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 10px;
    margin: 1rem 0;
}
.user-message {
    background-color: #e3f2fd;
    padding: 0.8rem;
    border-radius: 10px;
    margin: 0.5rem 0;
    border-left: 4px solid #2196f3;
}
.assistant-message {
    background-color: #f5f5f5;
    padding: 0.8rem;
    border-radius: 10px;
    margin: 0.5rem 0;
    border-left: 4px solid #666;
}
/* Light blue color for selected options in multiselect */
.stMultiSelect span[data-baseweb="tag"] {
    background-color: #e3f2fd !important;
    color: #1976d2 !important;
}
/* Hide the invisible trigger button */
button[data-testid="baseButton-secondary"] {
    display: none !important;
}
/* Make text input bigger like a text area */
.stTextInput > div > div > input {
    height: 150px !important;
    resize: vertical !important;
    padding: 12px !important;
}
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'current_query' not in st.session_state:
        st.session_state.current_query = ""
    if 'last_processed_query' not in st.session_state:
        st.session_state.last_processed_query = ""

def make_elasticsearch_request(query: str, categories: list) -> str:
    """Make request to Elasticsearch and return response"""
    elasticsearch_url = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
    category_str = ", ".join(categories) if categories else "No categories"
    try:
        response = requests.get(elasticsearch_url, timeout=5)
        return f"Query: '{query}'\nCategories: {category_str}\n\nElasticsearch Response:\n{response.text}"
    except requests.exceptions.ConnectionError:
        return f"Error: Could not connect to Elasticsearch at {elasticsearch_url}. Please ensure the service is running."
    except requests.exceptions.Timeout:
        return "Error: Request to Elasticsearch timed out."
    except Exception as e:
        return f"Error: {str(e)}"

def display_chat_history():
    """Display chat history in ChatGPT-like format"""
    if st.session_state.chat_history:
        st.markdown("### Conversation History")
        for i, chat in enumerate(st.session_state.chat_history):
            with st.container():
                category_display = ", ".join(chat['category']) if isinstance(chat['category'], list) else chat['category']
                st.markdown(f"""
                <div class="user-message">
                    <strong>You:</strong> {chat['query']} <em>(Categories: {category_display})</em>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="assistant-message">
                    <strong>Semantix:</strong><br>
                    <pre>{chat['response']}</pre>
                </div>
                """, unsafe_allow_html=True)

def main():
    """Main application function"""
    initialize_session_state()
    
    # Title and description
    st.markdown('<h1 class="main-title">Semantix</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Empower AI with semantic search</p>', unsafe_allow_html=True)
    
    # Display chat history
    display_chat_history()
    
    # Main input section - horizontal layout
    col1, col2 = st.columns([2, 5])
    
    with col1:
        # Category multiselect checkboxes
        categories = st.multiselect(
            "Select categories:",
            ["Jobs", "News"],
            default=[],
            placeholder="Search Category",
            help="Select one or more categories for your search",
            label_visibility="collapsed"
        )
    
    with col2:
        # Search input - using text_input with callback for Enter key submission
        def on_search_submit():
            if st.session_state.search_input and st.session_state.search_input.strip():
                query = st.session_state.search_input.strip()
                if query != st.session_state.get("last_processed_query", ""):
                    st.session_state.last_processed_query = query
                    # Process the query
                    with st.spinner('Processing your request...'):
                        response = make_elasticsearch_request(query, categories)
                        # Add to chat history
                        st.session_state.chat_history.append({
                            'query': query,
                            'category': categories,
                            'response': response
                        })
                    # Clear the input
                    st.session_state.search_input = ""
        
        query = st.text_input(
            "Enter your question or search query:",
            placeholder="Type your message here and press Enter...",
            label_visibility="collapsed",
            key="search_input",
            on_change=on_search_submit
        )

if __name__ == "__main__":
    main()