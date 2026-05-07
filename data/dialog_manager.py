"""对话管理器 — 从 JSON 台词包加载，加权随机选择，情绪标记"""

import json
import random
import os


class DialogManager:
    """台词管理器：从 JSON 台词包加载场景台词，支持加权选择和情绪标记"""

    def __init__(self, language: str = "zh_CN"):
        self.language = language
        self._dialogs = {}
        self._loaded_pack = None
        self._load_pack()

    def _load_pack(self):
        """加载对应语言的台词包"""
        pack_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"dialogs_{self.language}.json"
        )
        if not os.path.exists(pack_path):
            print(f"[DialogManager] Pack not found: {pack_path}")
            self._dialogs = {}
            return
        try:
            with open(pack_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._dialogs = {k: v for k, v in data.items() if not k.startswith("_")}
            self._loaded_pack = pack_path
            total = sum(len(v) for v in self._dialogs.values())
            print(f"[DialogManager] Loaded {len(self._dialogs)} scenes, {total} dialogs from {pack_path}")
        except Exception as e:
            print(f"[DialogManager] Load error: {e}")
            self._dialogs = {}

    def get_dialog(self, scene: str, **fmt_args) -> dict:
        """获取场景台词，加权随机返回一条

        返回: {"text": "...", "emotion": "...", "duration": 3000}
        """
        entries = self._dialogs.get(scene, [])
        if not entries:
            # 回退到通用 click 场景
            if scene not in ("click",):
                return self.get_dialog("click")
            return {"text": "", "emotion": "neutral", "duration": 3000}

        # 加权随机选择
        total_weight = sum(e.get("weight", 1) for e in entries)
        r = random.uniform(0, total_weight)
        cumulative = 0
        chosen = entries[0]
        for entry in entries:
            cumulative += entry.get("weight", 1)
            if r <= cumulative:
                chosen = entry
                break

        text = chosen["text"]
        emotion = chosen.get("emotion", "neutral")

        # 格式化文本（支持 {hour}, {battery}, {temp} 等占位符）
        if fmt_args:
            try:
                text = text.format(**fmt_args)
            except KeyError:
                pass  # 占位符不匹配时保持原样

        # 根据长度自动调节显示时长
        duration = max(2000, min(6000, len(text) * 80 + 1500))

        return {"text": text, "emotion": emotion, "duration": duration}

    def has_scene(self, scene: str) -> bool:
        """检查是否存在某场景"""
        return scene in self._dialogs and len(self._dialogs[scene]) > 0

    def switch_language(self, language: str):
        """切换语言并重新加载"""
        self.language = language
        self._load_pack()

    def get_all_scenes(self) -> list:
        """获取所有可用场景列表"""
        return list(self._dialogs.keys())

    def reload(self):
        """重新加载台词包"""
        self._load_pack()
