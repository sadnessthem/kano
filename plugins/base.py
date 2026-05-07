"""插件基类 — 所有插件继承此类"""

from PyQt5.QtCore import QObject, pyqtSignal


class PluginBase(QObject):
    """插件基类

    子类需实现:
        name (str): 插件名称
        description (str): 插件描述
        on_load(): 插件加载时调用
        on_unload(): 插件卸载时调用

    可选重写:
        on_event(event_type, data): 接收到全局事件时调用
        on_tick(): 每 tick 间隔调用（需设置 tick_interval）
    """

    name = "unnamed_plugin"
    description = ""
    tick_interval = 0  # tick 间隔（秒），0 表示不启用 tick

    plugin_event = pyqtSignal(str, dict)  # 插件可向系统发送事件

    def __init__(self, bridge, config, dialog_manager):
        super().__init__()
        self._bridge = bridge
        self._config = config
        self._dialog = dialog_manager
        self._enabled = True

    def on_load(self):
        """插件加载时调用"""
        pass

    def on_unload(self):
        """插件卸载时调用"""
        pass

    def on_event(self, event_type: str, data: dict):
        """全局事件回调"""
        pass

    def on_tick(self):
        """定时 tick 回调"""
        pass

    def show_dialog(self, text: str, duration: int = 3000):
        """显示对话气泡的快捷方法"""
        if self._bridge:
            self._bridge.send_command("showDialog", {
                "text": text, "duration": duration
            })

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
