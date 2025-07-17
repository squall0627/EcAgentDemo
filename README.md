# EcAgentDemo - AI-Powered E-commerce Management System

EcAgentDemo is an intelligent e-commerce back-office management system that combines traditional product and order management with advanced AI capabilities. The system uses AI agents to automate and enhance various e-commerce operations through natural language interactions.

## 🌟 Key Features

### Core E-commerce Management
- **Product Management**: Add, edit, and manage product catalogs
- **Order Processing**: Handle order creation, modification, and status updates
- **Order Cancellation**: Automated order cancellation workflows
- **Inventory Tracking**: Real-time inventory management

### AI-Powered Capabilities
- **Intelligent Agents**: Specialized AI agents for different business functions
  - Product Center Agent: Handles product-related queries and operations
  - Order Center Agent: Manages order processing and customer service
  - Task Planner: Orchestrates complex multi-step operations
- **Natural Language Interface**: Interact with the system using everyday language
- **Multi-LLM Support**: Compatible with OpenAI, Anthropic Claude, and Ollama models

### Advanced Input Methods
- **Voice Input**: Speak directly to the system using OpenAI Whisper API
- **Image Analysis**: Upload and analyze product images using GPT-4o Vision API
- **Text Chat**: Traditional text-based interaction

### Technical Features
- **Web Interface**: User-friendly browser-based interface
- **REST API**: Complete API for integration with other systems
- **Database Integration**: SQLAlchemy-based data persistence
- **Observability**: Built-in monitoring with Langfuse
- **Executable Packaging**: Can be packaged as standalone executable

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- OpenAI API key (required)
- Anthropic API key (optional)
- Internet connection for AI services

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd EcAgentDemo
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

   3. **Configure environment variables**

      Edit `.env` file and add your API keys:
      ```env
      OPENAI_API_KEY=your_openai_api_key_here
      ANTHROPIC_API_KEY=your_anthropic_api_key_here  # Optional
      GOOGLE_API_KEY=your_google_api_key_here        # Optional
      ACCESS_TOKEN_EXPIRE_MINUTES=60                 # Optional, default is 60 minutes
      API_BASE_URL=http://localhost:8000             # Adjust as needed
   
      LANGFUSE_PUBLIC_KEY=your_langfuse_public_key_here                             # Optional
      LANGFUSE_SECRET_KEY=your_langfuse_secret_key_here                             # Optional
      LANGFUSE_HOST=https://us.cloud.langfuse.com or https://eu.cloud.langfuse.com  # Optional
      ```

      Ensure you have the necessary API keys for OpenAI and Anthropic. The `API_BASE_URL` should match your deployment URL.
      ```

4. **Start the application**
   ```bash
   python api/main.py
   ```

   Or using uvicorn:
   ```bash
   uvicorn api.main:app --port 8000 --workers 4 --limit-concurrency 100 --log-level debug --timeout-keep-alive 60
   ```

5. **Access the application**
   - Main interface: http://localhost:8000/api/top
   - Settings page: http://localhost:80000/api/html/settings
   - API documentation: http://localhost:8000/docs

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

1. **Create docker-compose.yml**
   ```yaml
   version: '3.8'
   services:
     ecagent:
       build: .
       ports:
         - "8000:8000"
       environment:
         - OPENAI_API_KEY=${OPENAI_API_KEY}
         - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
         - GOOGLE_API_KEY=${GOOGLE_API_KEY}
         - ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES:-60}
         - API_BASE_URL=http://localhost:8000
         - LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY}
         - LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY}
         - LANGFUSE_HOST=${LANGFUSE_HOST}
       volumes:
         - ./data:/app/data
         - ./.env:/app/.env
   ```

2. **Build and run**
   ```bash
   docker-compose up --build
   ```

### Manual Docker Build

1. **Create Dockerfile**
   ```dockerfile
   FROM python:3.9-slim

   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt

   COPY . .
   EXPOSE 8000

   CMD ["python", "api/main.py"]
   ```

2. **Build and run**
   ```bash
   docker build -t ecagentdemo .
   docker run -p 8000:8000 --env-file .env ecagentdemo
   ```

## 📱 How to Use

### Basic Chat Interface
1. Navigate to http://localhost:8000/api/top
2. Type your questions or commands in natural language
3. The AI agents will process your request and provide responses

### Voice Input
1. Click the 🎤 microphone button next to the chat input
2. Allow microphone access when prompted
3. Speak your message clearly
4. The system will convert speech to text and process your request

### Image Analysis
1. Use the image upload feature in the chat interface
2. Upload product images (JPG, PNG, GIF, WebP supported)
3. Add text instructions about what you want to know
4. The AI will analyze the image and respond accordingly

### Example Interactions
- "Show me all products in the electronics category"
- "Create a new order for customer John Doe"
- "What's the status of order #12345?"
- "Cancel order #67890 and send notification to customer"
- "Upload this product image and tell me about its features"

## ⚙️ Configuration

### Environment Variables
- `OPENAI_API_KEY`: Required for AI functionality
- `ANTHROPIC_API_KEY`: Optional, for Claude models
- `GOOGLE_API_KEY`: Optional, for Google models
- `API_BASE_URL`: Base URL for the application
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time
- `LANGFUSE_*`: Optional, for observability tracking

### Supported AI Models
- **OpenAI**: GPT-3.5, GPT-4, GPT-4o (for vision)
- **Anthropic**: Claude models (requires Anthropic API key)
- **Google**: Gemini models (requires Google API key)
- **Ollama**: Local models (requires Ollama installation)

## 📦 Standalone Executable

The application can be packaged as a standalone executable using PyInstaller:

1. **Build executable**
   ```bash
   python build_executable.py
   ```

2. **Distribution**
   - The `dist/` folder contains the complete application
   - Share the entire `dist/` folder with end users
   - Users can run the application without Python installation

## 🔧 API Reference

### Main Endpoints
- `GET /`: API status
- `POST /api/chat/text_input`: Text-based chat
- `POST /api/chat/voice_input`: Voice input processing
- `POST /api/chat/image_input`: Image analysis
- `GET /api/product/*`: Product management
- `GET /api/order/*`: Order management
- `GET /api/settings/*`: System configuration

### Authentication
The system uses token-based authentication. Tokens expire based on the `ACCESS_TOKEN_EXPIRE_MINUTES` setting.

## 🧪 Testing

Run the test suite:
```bash
pytest test/
```

Test specific features:
```bash
python test_voice_functionality.py      # Voice input
python test_image_functionality.py      # Image analysis
python multi_agent_test.py             # AI agents
```

## 🛠️ Troubleshooting

### Common Issues

1. **"Service Unavailable" errors**
   - Check that your OpenAI API key is correctly set
   - Verify your API key has sufficient credits

2. **Voice input not working**
   - Ensure microphone permissions are granted
   - Use HTTPS for production deployments
   - Check that audio format is supported

3. **Image analysis failing**
   - Verify image format is supported (JPG, PNG, GIF, WebP)
   - Check image file size (follow OpenAI limits)
   - Ensure clear, readable images

4. **Database errors**
   - The system automatically creates SQLite database
   - Check file permissions in the application directory

### Performance Tips
- Use smaller image files for faster processing
- Consider using Ollama for local AI processing
- Monitor API usage to manage costs

## 🔒 Security Considerations

- Store API keys securely in environment variables
- Use HTTPS in production environments
- Regularly rotate API keys
- Monitor API usage and costs
- Implement proper access controls for production use

## 📄 License

This project is provided as-is for demonstration purposes. Please ensure compliance with all third-party service terms (OpenAI, Anthropic, Google, etc.) when using their APIs.

## 🤝 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the detailed feature documentation:
   - `IMAGE_UPLOAD_README.md` for image features
   - `VOICE_INPUT_README.md` for voice features
   - `README_Deploy.md` for deployment details
3. Ensure all environment variables are properly configured
4. Verify internet connectivity for AI services

---

**Note**: This system requires active internet connection and valid API keys for AI services. Local processing options are available through Ollama integration.
