"""窗口管理器：透明无边框窗口、拖拽、置顶、鼠标穿透"""

import sys
import os

from PyQt5.QtCore import Qt, QRect, QSize, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineSettings
from PyQt5.QtWebChannel import QWebChannel

from core.bridge import Bridge
from core.config_manager import ConfigManager


class WebEnginePage(QWebEnginePage):
    """自定义 WebEnginePage，允许加载本地文件 + 输出 JS 控制台"""

    js_console_message = pyqtSignal(str, str)  # level, message

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        """捕获 JS console 输出（重写 QWebEnginePage 虚方法）"""
        level_names = {0: "INFO", 1: "WARN", 2: "ERROR", 3: "DEBUG"}
        level_name = level_names.get(level, f"LEVEL{level}")
        print(f"[JS:{level_name}] {message}  (at {sourceID}:{lineNumber})", flush=True)
        self.js_console_message.emit(level_name, str(message))

    def acceptNavigationRequest(self, url, _type, isMainFrame):
        return True


class WindowManager(QMainWindow):
    """
    透明无边框置顶窗口，承载 QWebEngineView 渲染 Live2D
    """

    def __init__(self, config: ConfigManager, bridge: Bridge):
        super().__init__()
        self._config = config
        self._bridge = bridge
        # 拖拽状态（由 JS 桥事件控制）
        self._drag_initial_pos = None
        self._drag_initial_mouse = None

        self.is_topmost = config.get("window", "topmost", default=True)
        self.is_click_through = config.get("window", "click_through", default=False)
        self._scale = config.get("window", "scale", default=1.0)
        self._screen_index = config.get("window", "screen_index", default=0)
        self._edge_snap = config.get("window", "edge_snap", default=True)
        self._mini_mode = config.get("window", "mini_mode", default=False)
        self._snapped_to = None  # None | "left" | "right" | "top" | "bottom"

        self._setup_window()
        self._setup_webview()
        self._restore_position()

        # 连接 JS 桥事件：处理拖拽
        self._bridge.event_received.connect(self._on_bridge_event)

    def _setup_window(self):
        """配置窗口属性：透明、无边框、置顶"""
        # 无边框 + 置顶 + 工具窗口（不在任务栏）
        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.setAutoFillBackground(False)

        # 初始大小
        base_w, base_h = 400, 600
        self._base_size = QSize(base_w, base_h)
        if self._mini_mode:
            self.resize(150, 250)
            self.setMinimumSize(100, 150)
            self.setMaximumSize(300, 400)
        else:
            self.resize(int(base_w * self._scale), int(base_h * self._scale))
            self.setMinimumSize(200, 300)
            self.setMaximumSize(800, 1200)

    def _setup_webview(self):
        """初始化 QWebEngineView + QWebChannel + 事件过滤"""
        self._webview = QWebEngineView(self)
        self._webview.setAttribute(Qt.WA_TranslucentBackground)
        self._webview.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self._webview.setAutoFillBackground(False)
        self._webview.page().setBackgroundColor(Qt.transparent)

        # 允许本地文件 XHR 访问（Live2D 模型加载需要）
        settings = self._webview.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, True)
        settings.setAttribute(QWebEngineSettings.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, True)

        # 设置自定义 page（允许本地文件访问 + 输出 JS 控制台）
        self._page = WebEnginePage(self._webview)
        self._webview.setPage(self._page)

        # QWebChannel
        self._channel = QWebChannel()
        self._channel.registerObject("bridge", self._bridge)
        self._page.setWebChannel(self._channel)
        self._bridge.set_web_page(self._page)

        # 加载前端页面（使用 setHtml + baseUrl 避免 file:// WebGL 问题）
        web_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "web",
            "index.html"
        )
        from PyQt5.QtCore import QUrl
        with open(web_path, 'r', encoding='utf-8') as f:
            html = f.read()
        # Rewrite relative paths to absolute file:// paths
        base_url = QUrl.fromLocalFile(os.path.join(os.path.dirname(web_path), ''))
        self._page.setHtml(html, base_url)

        # 页面加载完成后再次确保透明背景
        # QWebEngineView 在 Windows 上加载页面后会重置背景色，
        # 需要在 loadFinished 时重新设置透明。
        self._page.loadFinished.connect(self._on_page_loaded)

        self.setCentralWidget(self._webview)

    def _on_page_loaded(self, ok: bool):
        """页面加载完成后，重新强制透明背景"""
        if not ok:
            return
        # 重新设置 page 透明背景（QWebEngine 可能在加载完成后重置）
        self._page.setBackgroundColor(Qt.transparent)
        js = (
            "document.documentElement.style.backgroundColor = 'transparent';"
            "document.body.style.backgroundColor = 'transparent';"
            "document.body.style.background = 'transparent';"
        )
        # 如果启动了迷你模式，发送 JS 指令（模型加载后生效）
        if self._mini_mode:
            js += (
                "var checkModel = setInterval(function(){"
                "if(window.live2dModel && window.live2dApp){"
                "window._normalScale = window.live2dModel.scale.x;"
                "var _z=3;"
                "window.live2dModel.scale.set(window._normalScale*_z,window._normalScale*_z);"
                "var _mh=window.live2dModel.height;"
                "window.live2dModel.position.set(0,_mh-window.innerHeight+30);"
                "window.live2dApp.stage.y = window.innerHeight;"
                "window.live2dApp.stage.x = window.innerWidth/2;"
                "_miniModeActive = true;"
                "clearInterval(checkModel);"
                "}},200);"
            )
        self._page.runJavaScript(js)

    # ---- JS 桥事件处理（拖拽） ----
    # QWebEngineView 的鼠标事件被 Chromium 内部消费，Qt eventFilter 无法捕获，
    # 改用 JS → QWebChannel → Bridge → WindowManager 路线。

    def _on_bridge_event(self, event_type: str, data: dict):
        """处理从 JS 桥发来的事件"""
        if event_type == "drag_start":
            self._drag_initial_pos = (self.x(), self.y())
            self._drag_initial_mouse = (data.get("mouseX", 0), data.get("mouseY", 0))

        elif event_type == "drag_move":
            if self._drag_initial_pos is None or self._drag_initial_mouse is None:
                return
            current_mouse_x = data.get("mouseX", 0)
            current_mouse_y = data.get("mouseY", 0)
            dx = current_mouse_x - self._drag_initial_mouse[0]
            dy = current_mouse_y - self._drag_initial_mouse[1]
            new_x = self._drag_initial_pos[0] + dx
            new_y = self._drag_initial_pos[1] + dy
            screens = QApplication.screens()
            screen_idx = min(self._screen_index, len(screens) - 1)
            geo = screens[screen_idx].availableGeometry()
            new_x = self._clamp_x(new_x, geo)
            new_y = self._clamp_y(new_y, geo)
            self.move(new_x, new_y)

        elif event_type == "drag_end":
            self._drag_initial_pos = None
            self._drag_initial_mouse = None
            if self._edge_snap:
                self._try_snap_to_edge()
            # 没有吸附则保存位置
            if self._snapped_to is None:
                self._config.set("window", "position", "x", self.x())
                self._config.set("window", "position", "y", self.y())

    def _restore_position(self):
        """从配置恢复窗口位置，支持多显示器"""
        screens = QApplication.screens()
        screen_idx = min(self._screen_index, len(screens) - 1)
        screen = screens[screen_idx]
        screen_geo = screen.availableGeometry()

        saved_x = self._config.get("window", "position", "x", default=None)
        saved_y = self._config.get("window", "position", "y", default=None)

        if saved_x is not None and saved_y is not None:
            x = self._clamp_x(saved_x, screen_geo)
            y = self._clamp_y(saved_y, screen_geo)
            self.move(x, y)
        else:
            # 在指定屏幕居中
            x = screen_geo.x() + (screen_geo.width() - self.width()) // 2
            y = screen_geo.y() + (screen_geo.height() - self.height()) // 2
            self.move(x, y)

    def _clamp_x(self, x: int, geo: QRect = None) -> int:
        if geo is None:
            geo = QApplication.primaryScreen().availableGeometry()
        margin = 10
        return max(margin, min(x, geo.width() - self.width() + margin))

    def _clamp_y(self, y: int, geo: QRect = None) -> int:
        if geo is None:
            geo = QApplication.primaryScreen().availableGeometry()
        margin = 10
        return max(margin, min(y, geo.height() - self.height() + margin))

    # ---- 边缘吸附 ----

    _SNAP_THRESHOLD = 30  # 距离边缘多少 px 时吸附

    def _try_snap_to_edge(self):
        """拖拽结束时检测是否靠近屏幕边缘，自动吸附"""
        screens = QApplication.screens()
        screen_idx = min(self._screen_index, len(screens) - 1)
        geo = screens[screen_idx].availableGeometry()
        x, y = self.x(), self.y()
        w, h = self.width(), self.height()
        snapped = None

        # 检测贴边
        if x <= geo.x() + self._SNAP_THRESHOLD:
            x = geo.x()
            snapped = "left"
        elif x + w >= geo.right() - self._SNAP_THRESHOLD:
            x = geo.right() - w
            snapped = "right"

        if y <= geo.y() + self._SNAP_THRESHOLD:
            y = geo.y()
            snapped = snapped or "top"
        elif y + h >= geo.bottom() - self._SNAP_THRESHOLD:
            y = geo.bottom() - h
            snapped = snapped or "bottom"

        if snapped:
            self.move(x, y)
            self._snapped_to = snapped
            self._config.set("window", "position", "x", x)
            self._config.set("window", "position", "y", y)
            self._bridge.send_command("showDialog", {
                "text": f"📌 已吸附到{'左' if snapped == 'left' else '右' if snapped == 'right' else '上' if snapped == 'top' else '下'}边缘",
                "duration": 2000
            })
        else:
            self._snapped_to = None

    # ---- 迷你模式 ----

    def toggle_mini_mode(self) -> bool:
        """切换迷你模式（只显示角色头部），返回新状态"""
        self._mini_mode = not self._mini_mode
        if self._mini_mode:
            # 缩小到只显示头部区域
            mini_w, mini_h = 150, 250
            self.setMinimumSize(100, 150)
            self.setMaximumSize(300, 400)
            self.resize(mini_w, mini_h)
            self._bridge.send_command("setMiniMode", {"enable": True})
        else:
            # 恢复正常尺寸
            self.setMinimumSize(200, 300)
            self.setMaximumSize(800, 1200)
            new_w = int(self._base_size.width() * self._scale)
            new_h = int(self._base_size.height() * self._scale)
            self.resize(new_w, new_h)
            self._bridge.send_command("setMiniMode", {"enable": False})
        self._config.set("window", "mini_mode", self._mini_mode)
        return self._mini_mode

    # ---- 公共 API ----

    def toggle_topmost(self) -> bool:
        """切换置顶，返回新状态"""
        self.is_topmost = not self.is_topmost
        if self.is_topmost:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()  # 切换 flags 后需要重新 show
        self._config.set("window", "topmost", self.is_topmost)
        return self.is_topmost

    def toggle_click_through(self) -> bool:
        """切换鼠标穿透（Windows 专用）"""
        self.is_click_through = not self.is_click_through
        self._apply_click_through()
        self._config.set("window", "click_through", self.is_click_through)
        return self.is_click_through

    def _apply_click_through(self):
        """通过 Windows API 设置鼠标穿透"""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            from ctypes import wintypes

            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x80000
            WS_EX_TRANSPARENT = 0x20

            hwnd = int(self.winId())
            user32 = ctypes.windll.user32

            current_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if self.is_click_through:
                new_style = current_style | WS_EX_LAYERED | WS_EX_TRANSPARENT
            else:
                new_style = current_style & ~(WS_EX_LAYERED | WS_EX_TRANSPARENT)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
        except Exception as e:
            print(f"[WindowManager] click-through failed: {e}")

    def set_scale(self, scale: float):
        """调整窗口缩放"""
        self._scale = max(0.5, min(2.0, scale))
        new_w = int(self._base_size.width() * self._scale)
        new_h = int(self._base_size.height() * self._scale)
        self.resize(new_w, new_h)
        self._bridge.send_command("setScale", {"scale": self._scale})
        self._config.set("window", "scale", self._scale)
