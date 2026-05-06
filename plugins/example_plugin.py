"""示例插件 — 演示插件系统用法"""

from plugins.base import PluginBase


class GreetingPlugin(PluginBase):
    """问候插件：用户在特定时间打开电脑时主动问候"""

    name = "问候插件"
    description = "在特定时间点（如工作开始、午休结束）主动打招呼"
    tick_interval = 3600  # 每小时检查一次

    def __init__(self, bridge, config, dialog_manager):
        super().__init__(bridge, config, dialog_manager)
        self._last_greeting_hour = -1

    def on_load(self):
        print(f"[{self.name}] 插件已加载")

    def on_unload(self):
        print(f"[{self.name}] 插件已卸载")

    def on_event(self, event_type: str, data: dict):
        """响应系统事件"""
        if event_type == "hourly_chime":
            hour = data.get("hour", -1)
            if hour == 9 and self._last_greeting_hour != 9:
                self._last_greeting_hour = 9
                self.show_dialog("新的一小时开始啦，加油工作~")

    def on_tick(self):
        """每小时 tick（示例功能）"""
        pass

    def set_greeting(self, text: str):
        """设置自定义问候语"""
        self._custom_greeting = text
