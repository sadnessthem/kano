"""通信桥：Python ↔ JS 双向通信（基于 QWebChannel）"""

import json
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal


class Bridge(QObject):
    """
    Python ↔ JS 双向通信桥

    JS 通过 channel.objects.bridge.handle_js_event(json_str) 调用 Python
    Python 通过 send_command(action, params) 向 JS 发送命令
    """

    # JS 上报的事件，转发给 behavior_engine
    event_received = pyqtSignal(str, dict)  # event_type, data

    def __init__(self, parent=None):
        super().__init__(parent)
        self._web_page = None

    def set_web_page(self, page):
        """设置 QWebEnginePage 用于执行 JS"""
        self._web_page = page

    @pyqtSlot(str)
    def handle_js_event(self, json_str: str):
        """接收 JS 上报的事件 JSON 字符串"""
        try:
            data = json.loads(json_str)
            event_type = data.get("event", "")
            event_data = data.get("data", {})
            self.event_received.emit(event_type, event_data)
        except json.JSONDecodeError:
            print(f"[Bridge] Invalid JSON from JS: {json_str}")

    @pyqtSlot()
    def on_frontend_ready(self):
        """JS 通知前端页面和 Live2D 模型已加载完成"""
        print("[Bridge] Frontend ready")
        self.event_received.emit("frontend_ready", {})

    def send_command(self, action: str, params: dict = None):
        """向 JS 发送命令"""
        if self._web_page is None:
            return
        cmd = json.dumps({
            "type": "command",
            "action": action,
            "params": params or {}
        }, ensure_ascii=False)
        js_code = f"window.receiveCommand({cmd})"
        self._web_page.runJavaScript(js_code)
