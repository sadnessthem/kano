"""待办事项管理器：JSON 文件存储、定时提醒"""

import os
import json
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class TodoItem:
    text: str
    done: bool = False
    created_at: float = 0.0
    due_at: Optional[float] = None      # 到期时间戳，None 表示无截止
    category: str = "default"
    remind_before_minutes: int = 0       # 提前 N 分钟提醒

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()

    @property
    def is_due(self) -> bool:
        return not self.done and self.due_at is not None and time.time() >= self.due_at

    @property
    def should_remind(self) -> bool:
        """是否到了需要提醒的时间"""
        if self.done or self.due_at is None:
            return False
        remind_at = self.due_at - self.remind_before_minutes * 60
        return time.time() >= remind_at


class TodoManager:
    """待办事项管理器"""

    def __init__(self, file_path: str = None):
        if file_path is None:
            file_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data",
                "todos.json"
            )
        self._file_path = file_path
        self._items: List[TodoItem] = []
        self._last_reminded: set = set()  # 已提醒过的 item id 集合
        self._load()

    # ---- 文件 I/O ----

    def _load(self):
        if not os.path.exists(self._file_path):
            self._items = []
            self._save()
            self._add_sample()
            return
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self._items = [TodoItem(**item) for item in raw]
        except (json.JSONDecodeError, IOError):
            self._items = []

    def _add_sample(self):
        """首次运行时添加示例待办"""
        now = time.time()
        self._items = [
            TodoItem(text="试试右键托盘 → 查看待办", category="default",
                     created_at=now - 3600, due_at=now + 7200),
            TodoItem(text="编辑 data/todos.json 添加自己的待办", category="default",
                     created_at=now - 1800),
        ]
        self._save()

    def _save(self):
        os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump([asdict(item) for item in self._items],
                      f, ensure_ascii=False, indent=2)

    # ---- 增删改查 ----

    def add(self, text: str, category: str = "default",
            due_in_minutes: int = 0, remind_before: int = 0) -> TodoItem:
        """添加待办事项"""
        item = TodoItem(
            text=text,
            category=category,
            created_at=time.time(),
            due_at=(time.time() + due_in_minutes * 60) if due_in_minutes > 0 else None,
            remind_before_minutes=remind_before,
        )
        self._items.append(item)
        self._save()
        return item

    def remove(self, index: int) -> bool:
        """删除指定项"""
        if 0 <= index < len(self._items):
            del self._items[index]
            self._save()
            return True
        return False

    def mark_done(self, index: int) -> bool:
        """标记完成"""
        if 0 <= index < len(self._items) and not self._items[index].done:
            self._items[index].done = True
            self._save()
            return True
        return False

    def get_pending(self) -> List[TodoItem]:
        """获取所有未完成事项"""
        return [item for item in self._items if not item.done]

    def get_due(self) -> List[TodoItem]:
        """获取当前到期的待办"""
        return [item for item in self._items if item.is_due]

    def get_needs_remind(self) -> List[TodoItem]:
        """获取需要提醒但尚未提醒的待办"""
        needs = []
        for i, item in enumerate(self._items):
            if item.should_remind and i not in self._last_reminded:
                needs.append(item)
                self._last_reminded.add(i)
        self._save()
        return needs

    def summary(self) -> str:
        """生成待办摘要文本"""
        pending = self.get_pending()
        if not pending:
            return "目前没有待办事项~ 轻松摸鱼中 ✨"
        lines = [f"还有 {len(pending)} 件事等着你哦:"]
        for i, item in enumerate(pending[:5], 1):
            due = ""
            if item.due_at:
                remaining = int(item.due_at - time.time())
                if remaining > 0:
                    due = f" [还剩 {remaining//60} 分钟]"
                else:
                    due = " [已到期!]"
            lines.append(f"  {i}. {item.text}{due}")
        if len(pending) > 5:
            lines.append(f"  ...还有 {len(pending) - 5} 项")
        return "\n".join(lines)

    @property
    def pending_count(self) -> int:
        return len(self.get_pending())
