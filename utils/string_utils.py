import re
from typing import LiteralString, Dict, Any, Type, TypedDict

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from ai_agents.base_agent import BaseAgentState


def clean_think_output(text: str) -> tuple[str, LiteralString | None]:
    thoughts = re.findall(r"<think>(.*?)</think>", text, flags=re.DOTALL)
    cleaned_text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    return cleaned_text, '\n'.join(thoughts) if thoughts else None


def serialize_state(state: BaseAgentState) -> Dict[str, Any]:
    """
    BaseAgentState を辞書形式に変換して序列化可能にする

    Args:
        state: 序列化対象のBaseAgentState

    Returns:
        Dict[str, Any]: 序列化可能な辞書
    """
    serialized = {}

    for key, value in state.items():
        if key == "messages":
            # LangChain メッセージオブジェクトを辞書形式に変換
            serialized[key] = [
                {
                    "type": msg.__class__.__name__,
                    "content": msg.content,
                    "additional_kwargs": getattr(msg, 'additional_kwargs', {}),
                    "response_metadata": getattr(msg, 'response_metadata', {}),
                }
                for msg in value
            ]
        elif key == "llm_info":
            # LLM情報を安全に序列化
            if value:
                serialized[key] = {
                    k: v for k, v in value.items()
                    if isinstance(v, (str, int, float, bool, list, dict, type(None)))
                }
            else:
                serialized[key] = value
        elif key == "response_data":
            # レスポンスデータを安全に序列化
            if value:
                serialized[key] = _serialize_dict_safely(value)
            else:
                serialized[key] = value
        else:
            # その他のフィールドはそのまま
            serialized[key] = value

    return serialized


def _serialize_dict_safely(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    辞書を安全に序列化する（再帰的に処理）
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = _serialize_dict_safely(value)
        elif isinstance(value, (str, int, float, bool, list, type(None))):
            result[key] = value
        else:
            # 序列化できないオブジェクトは文字列に変換
            result[key] = str(value)
    return result


def deserialize_state(serialized_data: Dict[str, Any], state_class: Type[TypedDict]) -> BaseAgentState:
    """
    序列化された辞書からBaseAgentStateを復元

    Args:
        serialized_data: 序列化された辞書データ
        state_class: 復元するBaseAgentStateのクラス

    Returns:
        BaseAgentState: 復元された状態
    """

    # メッセージを復元
    if "messages" in serialized_data:
        messages = []
        for msg_data in serialized_data["messages"]:
            msg_type = msg_data["type"]
            content = msg_data["content"]

            if msg_type == "HumanMessage":
                messages.append(HumanMessage(content=content))
            elif msg_type == "AIMessage":
                messages.append(AIMessage(content=content))
            elif msg_type == "SystemMessage":
                messages.append(SystemMessage(content=content))
            elif msg_type == "ToolMessage":
                messages.append(ToolMessage(content=content, **msg_data.get("additional_kwargs", {})))
            # 他のメッセージタイプも必要に応じて追加

        serialized_data["messages"] = messages

    return state_class(serialized_data)


import json


# 状態を JSON 文字列に変換
def state_to_json(state: BaseAgentState) -> str:
    """BaseAgentStateをJSON文字列に変換"""
    serialized = serialize_state(state)
    return json.dumps(serialized, ensure_ascii=False, indent=2)


# JSON 文字列から状態を復元
def json_to_state(json_str: str, state_class: Type[TypedDict]) -> BaseAgentState:
    """JSON文字列からBaseAgentStateを復元"""
    data = json.loads(json_str)
    return deserialize_state(data, state_class)
