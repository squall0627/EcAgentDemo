import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import importlib


class AgentHierarchyLoader:
    """エージェント階層構造を管理するローダークラス"""
    
    def __init__(self, config_path: str = None):
        """
        エージェント階層ローダーを初期化
        
        Args:
            config_path: 設定ファイルのパス（指定しない場合はデフォルトパスを使用）
        """
        if config_path is None:
            config_path = Path(__file__).parent / "agent_hierarchy.json"
        
        self.config_path = Path(config_path)
        self._config_cache = None
        self._load_config()
    
    def _load_config(self):
        """設定ファイルを読み込み"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config_cache = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"エージェント階層設定ファイルが見つかりません: {self.config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"エージェント階層設定ファイルのJSON形式が不正です: {e}")
    
    def reload_config(self):
        """設定を再読み込み"""
        self._config_cache = None
        self._load_config()
    
    def get_agent_hierarchy(self) -> Dict[str, Any]:
        """エージェント階層構造を取得"""
        return self._config_cache.get("agent_hierarchy", {})
    
    def get_entry_points(self) -> List[Dict[str, Any]]:
        """エントリーポイント一覧を取得"""
        return self._config_cache.get("entry_points", [])
    
    def get_agent_info(self, agent_key: str) -> Optional[Dict[str, Any]]:
        """指定されたエージェントの情報を取得"""
        hierarchy = self.get_agent_hierarchy()
        return self._find_agent_in_hierarchy(hierarchy, agent_key)
    
    def _find_agent_in_hierarchy(self, hierarchy: Dict[str, Any], target_key: str) -> Optional[Dict[str, Any]]:
        """階層構造から指定されたエージェントを検索"""
        for key, agent_info in hierarchy.items():
            if key == target_key:
                return agent_info
            
            # 子階層を再帰的に検索
            if "children" in agent_info and agent_info["children"]:
                result = self._find_agent_in_hierarchy(agent_info["children"], target_key)
                if result:
                    return result
        
        return None
    
    def get_all_agents_flat(self) -> List[Dict[str, Any]]:
        """全エージェントをフラットなリストで取得"""
        hierarchy = self.get_agent_hierarchy()
        agents = []
        self._flatten_hierarchy(hierarchy, agents)
        return agents
    
    def _flatten_hierarchy(self, hierarchy: Dict[str, Any], agents: List[Dict[str, Any]], parent_path: str = ""):
        """階層構造をフラットなリストに変換"""
        for key, agent_info in hierarchy.items():
            current_path = f"{parent_path}.{key}" if parent_path else key
            
            agent_data = {
                "key": key,
                "path": current_path,
                **agent_info
            }
            agents.append(agent_data)
            
            # 子階層を再帰的に処理
            if "children" in agent_info and agent_info["children"]:
                self._flatten_hierarchy(agent_info["children"], agents, current_path)
    
    def create_agent_instance(self, agent_key: str, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """指定されたエージェントのインスタンスを動的に作成"""
        agent_info = self.get_agent_info(agent_key)
        if not agent_info:
            raise ValueError(f"エージェント '{agent_key}' が見つかりません")
        
        try:
            # モジュールを動的にインポート
            module = importlib.import_module(agent_info["module_path"])
            
            # クラスを取得
            agent_class = getattr(module, agent_info["class_name"])
            
            # インスタンスを作成
            return agent_class(
                api_key=api_key,
                llm_type=llm_type,
                use_langfuse=use_langfuse
            )
            
        except ImportError as e:
            raise ImportError(f"エージェントモジュール '{agent_info['module_path']}' のインポートに失敗しました: {e}")
        except AttributeError as e:
            raise AttributeError(f"エージェントクラス '{agent_info['class_name']}' が見つかりません: {e}")
        except Exception as e:
            raise Exception(f"エージェントインスタンスの作成に失敗しました: {e}")
    
    def get_hierarchy_tree_display(self) -> str:
        """階層構造をツリー表示形式で取得"""
        hierarchy = self.get_agent_hierarchy()
        lines = []
        self._build_tree_display(hierarchy, lines, "")
        return "\n".join(lines)
    
    def _build_tree_display(self, hierarchy: Dict[str, Any], lines: List[str], prefix: str):
        """ツリー表示を構築"""
        items = list(hierarchy.items())
        for i, (key, agent_info) in enumerate(items):
            is_last = i == len(items) - 1
            current_prefix = "└─" if is_last else "├─"
            japanese_name = agent_info.get("japanese_name", key)
            lines.append(f"{prefix}{current_prefix}{japanese_name}")
            
            # 子階層がある場合は再帰的に処理
            if "children" in agent_info and agent_info["children"]:
                next_prefix = prefix + ("  " if is_last else "│ ")
                self._build_tree_display(agent_info["children"], lines, next_prefix)


# グローバルインスタンス
agent_hierarchy_loader = AgentHierarchyLoader()