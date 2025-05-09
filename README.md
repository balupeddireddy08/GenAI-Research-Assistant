#Summary of the application architecture:

1. **Core Application Files**:
   - `app/main.py` - Main FastAPI application entry point
   - `app/database.py` - Database configuration and connection handling
   - `app/config.py` - Environment-based application settings

2. **Database Models**:
   - `app/models/user.py` - User account database model
   - `app/models/conversation.py` - Conversation and message storage models

3. **API Structure**:
   - `app/api/api.py` - API router configuration
   - `app/api/endpoints/chat.py` - Chat functionality endpoints
   - `app/api/endpoints/history.py` - Conversation history management
   - `app/api/endpoints/recommendations.py` - Content recommendation endpoints

4. **Data Schemas**:
   - `app/schemas/conversation.py` - Conversation data validation models
   - `app/schemas/message.py` - Message data validation models

5. **Multi-Agent System**:
   - `app/services/orchestrator.py` - Central agent coordination
   - `app/services/search_agent.py` - Web search capabilities
   - `app/services/academic_agent.py` - Academic paper searching
   - `app/services/synthesis_agent.py` - Response synthesis from multiple sources
   - `app/services/chat_service.py` - Message processing service
   - `app/services/recommendations.py` - Content recommendation generation

6. **Utilities**:
   - `app/utils/llm_utils.py` - LLM provider integration (OpenAI)
   - `app/utils/gemini_utils.py` - Google Gemini model integration

7. **Frontend Application**:
   - `frontend/` - React-based user interface
   - `frontend/src/utils/api.js` - API client for backend communication

This is a sophisticated application implementing a multi-agent research assistant that can search academic papers, perform web searches, and generate comprehensive responses to research queries with proper citations and recommendations for further exploration.

## Running the Application

### Prerequisites

1. Python 3.9+ installed
2. Node.js 16+ installed
3. PostgreSQL database (optional, but recommended)

### Backend Setup

1. Create a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables in a `.env` file:
   ```
   # Database settings
   DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/research_assistant
   
   # API keys
   OPENAI_API_KEY=your_openai_key_here
   GOOGLE_API_KEY=your_google_key_here
   
   # LLM config
   PRIMARY_LLM=gpt-3.5-turbo  # or gemini-pro if using Google
   ```

4. Start the backend server:
   ```bash
   uvicorn app.main:app --reload
   ```

5. The API will be available at http://localhost:8000

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```

4. The application will open in your browser at http://localhost:3000

### Running Without a Database

If you don't have PostgreSQL installed, you can modify the application to work without it by setting an appropriate SQLite connection string:

```
DATABASE_URL=sqlite+aiosqlite:///./research_assistant.db
```

## API Model Configuration

The application now supports multiple AI model providers:

### OpenAI Models
- Configure with `OPENAI_API_KEY` in your .env file
- Supported models include:
  - gpt-3.5-turbo
  - gpt-3.5-turbo-16k
  - gpt-4
  - gpt-4o
  - gpt-4-32k

### Google Gemini Models
- Configure with `GOOGLE_API_KEY` in your .env file
- Supported models include:
  - gemini-pro
  - gemini-1.5-pro
  - gemini-1.5-flash
  - gemini-2.0-flash

### Setting the Active Model
Set your preferred model using the `PRIMARY_LLM` environment variable in your .env file:

```
# Use OpenAI's GPT-4
PRIMARY_LLM=gpt-4

# OR use Google's Gemini
PRIMARY_LLM=gemini-pro
```

## Troubleshooting Model Issues

If you encounter issues with model API calls:

1. **Check API Keys**: Ensure you have the correct API key for your selected model provider in the .env file.

2. **Verify Model Name**: Make sure the `PRIMARY_LLM` value exactly matches one of the supported model names listed above.

3. **API Rate Limits**: If you're encountering rate limit errors, consider using a different model or provider.

4. **Response Format**: Note that some features (like JSON response formatting) may work differently between OpenAI and Google models.

5. **Error Handling**: The application now provides more user-friendly error messages when API calls fail, making it easier to diagnose issues.

## Dependencies

Make sure you have all required dependencies installed:

```
pip install -r requirements.txt
```

The application requires both the OpenAI package and Google's generativeai package to support all model options.
