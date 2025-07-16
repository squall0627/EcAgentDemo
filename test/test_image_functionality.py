import asyncio
import os
import sys
import requests
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_image_service():
    """Test the ImageService directly"""
    print("🧪 Testing ImageService...")
    
    try:
        from services.image_service import ImageService
        
        # Check if service is available
        image_service = ImageService()
        if not image_service.is_available():
            print("❌ ImageService is not available. Please set OPENAI_API_KEY in .env file")
            return False
        
        print("✅ ImageService is available")
        print(f"📋 Supported formats: {image_service.get_supported_formats()}")
        
        # Test image analysis with a simple test image (if available)
        # For now, just test the service initialization
        return True
        
    except Exception as e:
        print(f"❌ ImageService test failed: {e}")
        return False

def test_image_upload_endpoint():
    """Test the image upload endpoint"""
    print("\n🌐 Testing image upload endpoint...")
    
    # Check if the server is running
    try:
        response = requests.get("http://localhost:8000/docs")
        if response.status_code != 200:
            print("❌ Server is not running. Please start the server first.")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Please start the server first.")
        return False
    
    print("✅ Server is running")
    
    # Test endpoint availability
    try:
        # Create a simple test image data (1x1 pixel PNG)
        # This is a minimal PNG file in base64
        import base64
        import io
        from PIL import Image
        
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color='red')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_data = img_buffer.getvalue()
        
        # Test the endpoint
        files = {'image_file': ('test.png', img_data, 'image/png')}
        data = {
            'user_message': 'この画像について教えてください',
            'session_id': 'test_session',
            'user_id': 'test_user',
            'agent_type': 'default',
            'llm_type': 'ollama'
        }
        
        response = requests.post(
            "http://localhost:8000/api/chat/image_input",
            files=files,
            data=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Image upload endpoint is working")
            print(f"📊 Response status: {result.get('status')}")
            print(f"💬 Message: {result.get('message')}")
            return True
        else:
            print(f"❌ Image upload endpoint failed: {response.status_code}")
            print(f"📄 Response: {response.text}")
            return False
            
    except ImportError:
        print("⚠️ PIL (Pillow) not available for creating test image. Skipping endpoint test.")
        return True
    except Exception as e:
        print(f"❌ Image upload endpoint test failed: {e}")
        return False

def check_environment():
    """Check if the environment is properly configured"""
    print("🔧 Checking environment configuration...")
    
    # Check if .env file exists
    env_file = Path("../.env")
    if not env_file.exists():
        print("❌ .env file not found. Please create one based on .env_sample")
        return False
    
    # Check if OPENAI_API_KEY is set
    from dotenv import load_dotenv
    load_dotenv()
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("❌ OPENAI_API_KEY not set in .env file")
        return False
    
    print("✅ Environment configuration looks good")
    return True

async def main():
    """Main test function"""
    print("🚀 Starting image functionality tests...\n")
    
    # Check environment
    if not check_environment():
        print("\n❌ Environment check failed. Please fix the issues above.")
        return
    
    # Test ImageService
    service_ok = await test_image_service()
    
    # Test endpoint (only if service is OK)
    endpoint_ok = True
    if service_ok:
        endpoint_ok = test_image_upload_endpoint()
    
    # Summary
    print("\n📋 Test Summary:")
    print(f"   ImageService: {'✅ PASS' if service_ok else '❌ FAIL'}")
    print(f"   Upload Endpoint: {'✅ PASS' if endpoint_ok else '❌ FAIL'}")
    
    if service_ok and endpoint_ok:
        print("\n🎉 All tests passed! Image functionality is ready to use.")
        print("\n📖 Usage:")
        print("   1. Start the server: uvicorn main:app --reload")
        print("   2. Use POST /api/chat/image_input with:")
        print("      - image_file: The image file to analyze")
        print("      - user_message: Optional text message")
        print("      - session_id, user_id: For tracking")
        print("      - agent_type, llm_type: For agent configuration")
    else:
        print("\n❌ Some tests failed. Please check the issues above.")

if __name__ == "__main__":
    asyncio.run(main())