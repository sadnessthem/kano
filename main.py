"""Kanban — 桌面 Live2D 看板娘 · 程序入口"""

import sys
import os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import os

# 强制 QWebEngine 使用 ANGLE 图形后端（解决 WebGL 兼容性）
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS",
    "--use-gl=angle --enable-webgl --enable-transparent-visuals --no-sandbox")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
# 必须在 QApplication 创建前导入 WebEngineWidgets
from PyQt5.QtWebEngineWidgets import QWebEngineView

QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)  # 关闭窗口不退出（最小化到托盘）

from core.config_manager import ConfigManager
from core.bridge import Bridge
from core.window_manager import WindowManager
from core.behavior_engine import BehaviorEngine
from core.backend_services import BackendServices
from core.pomodoro_timer import PomodoroTimer
from core.tray_manager import TrayManager
from data.dialog_manager import DialogManager
from data.todo_manager import TodoManager
from plugins.loader import PluginLoader


def main():
    # 1. 配置
    config = ConfigManager()

    # 2. 通信桥
    bridge = Bridge()

    # 3. 主窗口
    window = WindowManager(config, bridge)

    # 4. 对话管理器
    dialog_manager = DialogManager(language=config.get("app", "language", default="zh_CN"))

    # 5. 后台服务（空闲检测、系统监控、整点报时、天气）
    services = BackendServices(config)

    # 5b. 待办管理器（注入到后台服务中）
    todo_manager = TodoManager()
    services.set_todo_manager(todo_manager)

    # 6. 行为引擎（接入桥、对话管理器、配置、后台服务）
    behavior = BehaviorEngine(bridge, config, dialog_manager,
                              backend_services=services)

    # 7. 启动所有服务
    services.start_all()
    behavior.start()

    # 8. 插件加载器
    plugin_loader = PluginLoader(bridge, config, dialog_manager)
    plugin_loader.load_all()

    # 9. 番茄钟
    pomodoro = PomodoroTimer(work_minutes=25, break_minutes=5)

    # 10. 系统托盘
    tray = TrayManager(window, bridge, config=config, behavior=behavior,
                       services=services, pomodoro=pomodoro)

    # 11. 显示窗口
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
