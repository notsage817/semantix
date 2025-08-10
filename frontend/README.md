# Semantix Frontend

A ChatGPT-like web interface built with Streamlit for semantic search functionality.

## Overview

This frontend provides an intuitive chat interface that allows users to:
- Submit queries with category selection
- View conversation history in ChatGPT-style format
- Interact with Elasticsearch backend at localhost:9200
- Experience responsive, modern UI design

## Components

### Core Files

- **`app.py`**: Main Streamlit application with chat interface, conversation management, and Elasticsearch integration
- **`requirements.txt`**: Python dependencies (Streamlit, requests)

### Features

- **Chat Interface**: Center-positioned search box with submit button
- **Category Selection**: Dropdown menu (currently supports "Jobs" category)
- **Conversation History**: ChatGPT-like display of previous queries and responses
- **Elasticsearch Integration**: Connects to localhost:9200 for search functionality
- **Responsive Design**: Custom CSS styling for modern appearance

## Docker Setup

### Prerequisites

- Docker and Docker Compose installed
- Elasticsearch running on localhost:9200 (for full functionality)

### Quick Start

1. **Build and run with Docker Compose** (Recommended):
   ```bash
   cd docker
   docker-compose up --build
   ```

2. **Access the application**:
   Open your browser to http://localhost:8501

### Alternative Docker Commands

1. **Build the Docker image**:
   ```bash
   docker build -f docker/Dockerfile -t semantix-frontend .
   ```

2. **Run the container**:
   ```bash
   docker run -p 8501:8501 semantix-frontend
   ```

## Local Development

### Setup

1. **Install dependencies**:
   ```bash
   cd frontend
   pip install -r requirements.txt
   ```

2. **Run the application**:
   ```bash
   streamlit run app.py
   ```

3. **Access locally**:
   Open http://localhost:8501 in your browser

## Usage

1. **Select Category**: Choose "Jobs" from the dropdown menu
2. **Enter Query**: Type your search question in the text input
3. **Submit**: Click the Submit button to process your request
4. **View Results**: See the Elasticsearch response displayed below
5. **Continue Conversation**: Previous queries and responses remain visible above the input area

## Architecture

### Session Management
- Uses Streamlit's session state for conversation persistence
- Chat history stored in `st.session_state.chat_history`
- Automatic UI refresh after each query submission

### Elasticsearch Integration
- Makes GET requests to http://localhost:9200
- Handles connection errors gracefully
- Displays raw Elasticsearch responses

### Styling
- Custom CSS for ChatGPT-like appearance
- Responsive layout with centered content
- Color-coded message types (user vs assistant)

## Configuration

### Environment Variables
- No environment variables required for basic functionality
- Elasticsearch endpoint is currently hardcoded to localhost:9200

### Customization
- Modify `ELASTICSEARCH_URL` in app.py to change backend endpoint
- Add new categories by updating the selectbox options
- Customize styling by modifying the CSS in the markdown section

## Troubleshooting

### Common Issues

1. **"Could not connect to Elasticsearch"**:
   - Ensure Elasticsearch is running on localhost:9200
   - Check if port 9200 is accessible
   - Verify network connectivity

2. **Docker build failures**:
   - Ensure you're running commands from the project root
   - Check Docker daemon is running
   - Verify all required files are present

3. **Port 8501 already in use**:
   - Stop other Streamlit applications
   - Use different port: `docker run -p 8502:8501 semantix-frontend`

### Development Tips

- Use `streamlit run app.py --server.runOnSave=true` for auto-reload during development
- Check browser developer console for JavaScript errors
- Monitor Docker logs: `docker-compose logs -f semantix-frontend`

## Future Enhancements

- Multiple category support
- Advanced Elasticsearch query building
- User authentication
- Response formatting and parsing
- Export conversation history
- Real-time search suggestions
