from ai_agents.order_center.tools.order_detail_agent_tool import OrderDetailAgentTool
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
if api_key:
    tool = OrderDetailAgentTool(api_key=api_key, llm_type='openai_gpt4')
    print('OrderDetailAgentTool works fine')
else:
    print('No API key found')