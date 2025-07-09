from ai_agents.product_center.tools.product_detail_agent_tool import ProductDetailAgentTool
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
if api_key:
    tool = ProductDetailAgentTool(api_key=api_key, llm_type='openai_gpt4')
    print('ProductDetailAgentTool works fine')
else:
    print('No API key found')