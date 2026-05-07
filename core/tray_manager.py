"""系统托盘管理器 — 增强菜单、设置面板入口"""

import os
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QDialog, QMessageBox, QApplication, QInputDialog, QLineEdit
from PyQt5.QtGui import QIcon, QPixmap


# 常用城市列表
_COMMON_CITIES = [
    ("自动检测", ""),
    ("北京", "beijing"), ("上海", "shanghai"), ("广州", "guangzhou"),
    ("深圳", "shenzhen"), ("杭州", "hangzhou"), ("成都", "chengdu"),
    ("武汉", "wuhan"), ("南京", "nanjing"), ("重庆", "chongqing"),
    ("西安", "xian"), ("苏州", "suzhou"), ("天津", "tianjin"),
    ("长沙", "changsha"), ("郑州", "zhengzhou"), ("东莞", "dongguan"),
    ("青岛", "qingdao"), ("沈阳", "shenyang"), ("宁波", "ningbo"),
    ("昆明", "kunming"), ("大连", "dalian"), ("厦门", "xiamen"),
    ("合肥", "hefei"), ("佛山", "foshan"), ("福州", "fuzhou"),
    ("哈尔滨", "haerbin"), ("济南", "jinan"), ("温州", "wenzhou"),
    ("长春", "changchun"), ("石家庄", "shijiazhuang"), ("常州", "changzhou"),
    ("泉州", "quanzhou"), ("南宁", "nanning"), ("贵阳", "guiyang"),
    ("南昌", "nanchang"), ("太原", "taiyuan"), ("烟台", "yantai"),
    ("嘉兴", "jiaxing"), ("南通", "nantong"), ("金华", "jinhua"),
    ("珠海", "zhuhai"), ("惠州", "huizhou"), ("徐州", "xuzhou"),
    ("海口", "haikou"), ("乌鲁木齐", "wulumuqi"), ("绍兴", "shaoxing"),
    ("中山", "zhongshan"), ("台州", "taizhou"), ("兰州", "lanzhou"),
    ("纽约", "new york"), ("伦敦", "london"), ("东京", "tokyo"),
    ("巴黎", "paris"), ("首尔", "seoul"), ("悉尼", "sydney"),
    ("新加坡", "singapore"),
]


class TrayManager:
    """管理系统托盘图标和右键菜单"""

    def __init__(self, window, bridge, config=None, behavior=None, services=None, pomodoro=None, todo_manager=None):
        self._window = window
        self._bridge = bridge
        self._config = config
        self._behavior = behavior
        self._services = services
        self._pomodoro = pomodoro
        self._todo_manager = todo_manager
        self._todo_menu = None
        self._tray = None
        self._icon = self._load_icon()
        self._setup_tray()

    @staticmethod
    def _load_icon() -> QIcon:
        """加载托盘图标"""
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "resources", "icon.svg"
        )
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            if not icon.isNull():
                return icon
        # 回退：程序化绘制
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.Antialiasing)
        grad = QRadialGradient(32, 32, 32)
        grad.setColorAt(0, QColor("#E87EA0"))
        grad.setColorAt(0.7, QColor("#C06080"))
        grad.setColorAt(1, QColor("#8B5F7F"))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.NoPen)
        p.drawEllipse(2, 2, 60, 60)
        p.setBrush(QColor("#3D2460"))
        p.drawEllipse(20, 26, 8, 10)
        p.drawEllipse(36, 26, 8, 10)
        p.setBrush(QColor("#fff"))
        p.drawEllipse(22, 27, 3, 3)
        p.drawEllipse(38, 27, 3, 3)
        pen = QPen(QColor("#D4607F"), 1.5)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(24, 30, 16, 12, 0, -180 * 16)
        p.end()
        return QIcon(pixmap)

    def _setup_tray(self):
        """初始化系统托盘"""
        self._tray = QSystemTrayIcon(self._window)
        self._tray.setIcon(self._icon)
        self._tray.setToolTip("Kanban - 桌面看板娘")
        self._tray.activated.connect(self._on_tray_activated)

        self._menu = QMenu()
        self._toggle_act = self._menu.addAction("隐藏")
        self._toggle_act.triggered.connect(self._toggle_visibility)

        self._menu.addSeparator()
        self._topmost_act = self._menu.addAction("保持置顶")
        self._topmost_act.setCheckable(True)
        self._topmost_act.setChecked(self._window.is_topmost)
        self._topmost_act.triggered.connect(self._on_topmost_triggered)

        self._click_through_act = self._menu.addAction("鼠标穿透模式")
        self._click_through_act.setCheckable(True)
        self._click_through_act.setChecked(getattr(self._window, 'is_click_through', False))
        self._click_through_act.triggered.connect(self._on_click_through_triggered)

        self._mini_mode_act = self._menu.addAction("迷你模式")
        self._mini_mode_act.setCheckable(True)
        self._mini_mode_act.setChecked(getattr(self._window, '_mini_mode', False))
        self._mini_mode_act.triggered.connect(self._on_mini_mode_triggered)

        # ── 待办子菜单（动态刷新） ──
        self._todo_menu = QMenu("📋 待办事项", self._menu)
        self._todo_menu.aboutToShow.connect(self._refresh_todo_menu)
        self._menu.addMenu(self._todo_menu)

        weather_act = self._menu.addAction("🌤 播报天气")
        weather_act.triggered.connect(self._say_weather)

        reload_act = self._menu.addAction("🔄 重新加载模型")
        reload_act.triggered.connect(lambda: self._bridge.send_command("reload"))

        self._menu.addSeparator()
        fortune_act = self._menu.addAction("🎲 今日运势")
        fortune_act.triggered.connect(self._show_fortune)

        self._pomodoro_act = self._menu.addAction("🍅 开始专注")
        self._pomodoro_act.triggered.connect(self._on_pomodoro_triggered)
        if self._pomodoro:
            self._pomodoro.tick.connect(self._on_pomodoro_tick)
            self._pomodoro.finished.connect(self._on_pomodoro_finished)

        draw_act = self._menu.addAction("🎴 抽签")
        draw_act.triggered.connect(self._draw_lot)

        self._menu.addSeparator()
        settings_act = self._menu.addAction("设置...")
        settings_act.triggered.connect(self._open_settings)

        about_act = self._menu.addAction("关于 Kanban")
        about_act.triggered.connect(self._show_about)

        self._menu.addSeparator()
        quit_act = self._menu.addAction("退出")
        quit_act.triggered.connect(self._quit_app)

        self._tray.setContextMenu(self._menu)
        self._tray.show()

    def _on_topmost_triggered(self, checked: bool):
        self._window.toggle_topmost()
        self._topmost_act.setChecked(self._window.is_topmost)

    def _on_click_through_triggered(self, checked: bool):
        self._window.toggle_click_through()
        self._click_through_act.setChecked(getattr(self._window, 'is_click_through', False))

    def _on_mini_mode_triggered(self, checked: bool):
        new_state = self._window.toggle_mini_mode()
        self._mini_mode_act.setChecked(new_state)
        if new_state:
            self._window._bridge.send_command("showDialog", {
                "text": "✨ 切换到迷你模式~", "duration": 2000
            })

    def _toggle_visibility(self):
        if self._window.isVisible():
            self._window.hide()
            self._toggle_act.setText("显示")
        else:
            self._window.show()
            self._window.activateWindow()
            self._toggle_act.setText("隐藏")

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            if not self._window.isVisible():
                self._window.show()
                self._toggle_act.setText("隐藏")

    def _say_weather(self):
        """播报天气（异步）"""
        if self._behavior and self._services:
            city = self._config.get("weather", "city", default="beijing") if self._config else "beijing"
            self._services.weather_result.connect(self._on_weather_result)
            self._services.fetch_weather(city)
        elif self._behavior:
            self._behavior.show_dialog("天气服务暂未启动~", 3000)

    def _on_weather_result(self, city: str, data: dict):
        try:
            self._services.weather_result.disconnect(self._on_weather_result)
        except TypeError:
            pass
        if data and self._behavior:
            self._behavior.say_weather(data)

    def _open_settings(self):
        dlg = SettingsDialog(self._window, self._config)
        result = dlg.exec_()
        if result == QDialog.Accepted:
            # 对话框已完全关闭，延迟一帧应用所有运行时变更
            QTimer.singleShot(0, self._apply_settings)

    def _apply_settings(self):
        """对话框关闭后应用运行时设置（不在 modal event loop 中执行）"""
        cfg = self._config
        scale = cfg.get("window", "scale", default=1.0)
        self._window.set_scale(scale)
        topmost_cfg = cfg.get("window", "topmost", default=True)
        if topmost_cfg != self._window.is_topmost:
            self._window.toggle_topmost()
        click_through_cfg = cfg.get("window", "click_through", default=False)
        if click_through_cfg != getattr(self._window, 'is_click_through', False):
            self._window.toggle_click_through()
        if self._services:
            self._services.restart_reminder()

    def _refresh_todo_menu(self):
        """动态构建待办子菜单内容"""
        self._todo_menu.clear()

        tm = self._todo_manager
        if tm is None:
            self._todo_menu.addAction("⚠ 待办服务未启用").setEnabled(False)
            return

        pending = tm.get_pending()
        count = len(pending)

        # ── 顶部：查看全部（弹出气泡） ──
        summary_action = self._todo_menu.addAction(
            f"📋 查看待办  ({count})" if count else "📋 查看待办"
        )
        summary_action.triggered.connect(self._show_todos)

        self._todo_menu.addSeparator()

        if not pending:
            noop = self._todo_menu.addAction("✨ 没有待办，轻松摸鱼~")
            noop.setEnabled(False)
        else:
            # ── 每个待办作为可点击菜单项 ──
            for i, item in enumerate(pending):
                text = item.text
                if len(text) > 28:
                    text = text[:26] + "…"

                # 截止标记
                suffix = ""
                if item.due_at:
                    import time
                    remaining = int(item.due_at - time.time())
                    if remaining <= 0:
                        suffix = "  ⏰已到期!"
                    elif remaining <= 3600:
                        suffix = f"  ⏰{max(1, remaining//60)}分钟"
                    else:
                        suffix = f"  ⏰{remaining//3600}h"

                label = f"☐ {text}{suffix}"
                act = self._todo_menu.addAction(label)

                # 用闭包捕获当前 index
                idx = i
                act.triggered.connect(lambda checked, ix=idx: self._mark_todo_done(ix))

        self._todo_menu.addSeparator()

        # ── 添加新待办 ──
        add_act = self._todo_menu.addAction("＋ 添加待办…")
        add_act.triggered.connect(self._add_todo_dialog)

    def _show_todos(self):
        """在角色气泡中显示待办摘要"""
        if self._todo_manager:
            summary = self._todo_manager.summary()
        elif self._services:
            summary = self._services.query_todo_summary()
        else:
            summary = "待办服务暂未启用~"
        if self._behavior:
            self._behavior.show_dialog(summary, 6000)

    def _mark_todo_done(self, index: int):
        """从待办子菜单标记完成"""
        if self._todo_manager and self._todo_manager.mark_done(index):
            if self._behavior:
                self._behavior.show_dialog("✅ 已标记完成~", 2000)
            # 强制刷新子菜单
            self._refresh_todo_menu()

    def _add_todo_dialog(self):
        """弹出输入框添加新待办"""
        text, ok = QInputDialog.getText(
            self._window, "添加待办", "输入待办内容:",
            QLineEdit.Normal, ""
        )
        if ok and text.strip():
            self._todo_manager.add(text.strip())
            if self._behavior:
                self._behavior.show_dialog(f"📌 已添加待办:\n{text.strip()}", 3000)
            self._refresh_todo_menu()

    def _show_fortune(self):
        """显示今日运势"""
        from core.fortune import get_daily_fortune
        if self._behavior:
            text = get_daily_fortune()
            self._behavior.show_dialog(text, 5000)

    def _draw_lot(self):
        """随机抽签"""
        from core.fortune import get_random_fortune
        if self._behavior:
            text = get_random_fortune()
            self._behavior.show_dialog(text, 5000)

    def _on_pomodoro_triggered(self):
        """番茄钟点击处理"""
        if not self._pomodoro:
            if self._behavior:
                self._behavior.show_dialog("番茄钟未加载~", 3000)
            return
        state = self._pomodoro.state
        if state == "idle":
            self._pomodoro.start_work()
            if self._behavior:
                self._behavior.show_dialog("🍅 专注开始！25分钟加油~", 3000)
        elif state == "working":
            self._pomodoro.reset()
            self._pomodoro_act.setText("🍅 开始专注")
            if self._behavior:
                self._behavior.show_dialog("⏹ 专注已结束", 2000)
        elif state == "break":
            self._pomodoro.reset()
            self._pomodoro_act.setText("🍅 开始专注")
            if self._behavior:
                self._behavior.show_dialog("⏹ 休息已结束", 2000)

    def _on_pomodoro_tick(self, remaining: int, total: int):
        """每秒更新番茄钟菜单文字"""
        mm = remaining // 60
        ss = remaining % 60
        if self._pomodoro.state == "working":
            self._pomodoro_act.setText(f"🍅 工作中  {mm:02d}:{ss:02d}")
        elif self._pomodoro.state == "break":
            self._pomodoro_act.setText(f"☕ 休息中  {mm:02d}:{ss:02d}")

    def _on_pomodoro_finished(self, mode: str):
        """番茄钟时段结束"""
        if mode == "working":
            self._pomodoro_act.setText("☕ 休息中  +5s")
            if self._behavior:
                self._behavior.show_dialog("🎉 专注完成！休息5分钟吧~", 4000)
            QTimer.singleShot(1500, self._pomodoro.start_break)
        else:  # break
            self._pomodoro_act.setText("🍅 开始专注")
            if self._behavior:
                self._behavior.show_dialog("☕ 休息结束！再开始一轮吧~", 3000)

    def _show_about(self):
        QMessageBox.about(
            self._window, "关于 Kanban",
            "Kanban — 桌面 Live2D 看板娘\n\n"
            "基于 PyQt5 + PixiJS 6 + Live2D Cubism 5\n\n"
            "版本 1.0\n"
            "使用 live2d cubism core 5.1.0"
        )

    def _quit_app(self):
        if self._services:
            self._services.stop_all()
        QApplication.quit()


class SettingsDialog(QDialog):
    """设置面板 — 二次元风格标签页"""

    _ANIME_STYLE = """
        /* ===== 整体背景 ===== */
        QDialog {
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #FFF5F9, stop:0.5 #FEF8FF, stop:1 #F8EEFF
            );
        }
        /* ===== 标签页容器 ===== */
        QTabWidget::pane {
            border: 1px solid #E8C8D8;
            border-radius: 10px;
            background: rgba(255,255,255,0.85);
            padding: 6px;
        }
        QTabBar::tab {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #FCE4EC, stop:1 #F8D0E0);
            color: #8B5F7F;
            border: none;
            padding: 8px 16px;
            margin: 0 2px;
            border-radius: 8px 8px 0 0;
            font-size: 12px;
            font-weight: bold;
            min-width: 60px;
        }
        QTabBar::tab:selected {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #E87EA0, stop:1 #D4607F);
            color: white;
        }
        QTabBar::tab:hover:!selected {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #F0D0DC, stop:1 #ECC0D0);
        }
        /* ===== GroupBox ===== */
        QGroupBox {
            border: 1px solid #E8D0E4;
            border-radius: 8px;
            margin-top: 14px;
            padding: 12px 8px 8px 8px;
            font-size: 12px;
            font-weight: bold;
            color: #6B3F6F;
            background: rgba(255,248,252,0.5);
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 8px;
            background: rgba(255,255,255,0.7);
            border-radius: 4px;
        }
        /* ===== Slider ===== */
        QSlider::groove:horizontal {
            height: 6px;
            background: #F0E0E8;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #E87EA0, stop:1 #D4607F);
            width: 18px;
            height: 18px;
            margin: -6px 0;
            border-radius: 9px;
            border: 2px solid white;
        }
        QSlider::handle:horizontal:hover {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #F090B0, stop:1 #E07090);
            width: 20px;
            height: 20px;
            margin: -7px 0;
        }
        QSlider::sub-page:horizontal {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #E87EA0, stop:1 #D4A0C0);
            border-radius: 3px;
        }
        QSlider::tick {
            color: #D0B0C0;
        }
        /* ===== ComboBox ===== */
        QComboBox {
            border: 1px solid #E8D0DE;
            border-radius: 6px;
            padding: 5px 10px;
            background: white;
            color: #3D2460;
            min-height: 20px;
        }
        QComboBox:hover {
            border-color: #E87EA0;
        }
        QComboBox:focus {
            border-color: #D4607F;
        }
        QComboBox::drop-down {
            border: none;
            width: 24px;
            border-left: 1px solid #F0E0E8;
            border-top-right-radius: 6px;
            border-bottom-right-radius: 6px;
        }
        QComboBox::down-arrow {
            image: none;
            border: none;
        }
        QComboBox QAbstractItemView {
            border: 1px solid #E8D0DE;
            border-radius: 6px;
            background: white;
            selection-background-color: #FCE4EC;
            selection-color: #3D2460;
            padding: 4px;
        }
        /* ===== SpinBox ===== */
        QSpinBox {
            border: 1px solid #E8D0DE;
            border-radius: 6px;
            padding: 5px 10px;
            background: white;
            color: #3D2460;
            min-height: 20px;
        }
        QSpinBox:hover {
            border-color: #E87EA0;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            border: none;
            width: 20px;
        }
        /* ===== CheckBox ===== */
        QCheckBox {
            spacing: 8px;
            color: #4A3050;
            font-size: 12px;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 1.5px solid #D0B0C4;
            border-radius: 4px;
            background: white;
        }
        QCheckBox::indicator:checked {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #E87EA0, stop:1 #D4607F);
            border-color: #D4607F;
        }
        QCheckBox::indicator:hover {
            border-color: #E87EA0;
        }
        /* ===== PushButton ===== */
        QPushButton {
            border: none;
            border-radius: 8px;
            padding: 8px 28px;
            font-size: 13px;
            font-weight: bold;
        }
        /* ===== QLabel ===== */
        QLabel {
            color: #4A3050;
        }
        /* ===== ScrollArea (inner tab pages) ===== */
        QScrollArea {
            border: none;
            background: transparent;
        }
    """

    def __init__(self, parent, config):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("⚡ Kanban 设置")
        self.resize(520, 560)
        self.setMinimumSize(460, 480)
        self.setStyleSheet(self._ANIME_STYLE)
        self._current_page = 0
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        from PyQt5.QtWidgets import (
            QVBoxLayout, QHBoxLayout, QLabel, QSlider, QTabWidget,
            QComboBox, QCheckBox, QPushButton, QWidget,
            QFormLayout, QSpinBox, QGroupBox, QFrame
        )
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QApplication

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 8)
        main_layout.setSpacing(8)

        # ---- 顶部装饰横幅 ----
        banner = QFrame()
        banner.setStyleSheet(
            "QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #E87EA0,stop:0.5 #D4607F,stop:1 #C06080);"
            "border-radius:10px;padding:10px 16px;}"
        )
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(12, 6, 12, 6)
        title_label = QLabel("✦ Kanban 设定 ✦")
        title_label.setStyleSheet("color:white;font-size:16px;font-weight:bold;")
        subtitle_label = QLabel("自定义你的桌面看板娘")
        subtitle_label.setStyleSheet("color:rgba(255,255,255,0.75);font-size:11px;")
        banner_layout.addWidget(title_label)
        banner_layout.addStretch()
        banner_layout.addWidget(subtitle_label)
        main_layout.addWidget(banner)

        # ---- 标签页 ----
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        main_layout.addWidget(self._tabs)

        # ===== 🌸 窗口 =====
        win_page = QWidget()
        win_layout = QVBoxLayout(win_page)
        win_layout.setSpacing(8)
        win_form = QFormLayout()
        win_form.setSpacing(8)
        win_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        win_layout.addLayout(win_form)

        scale_row = QHBoxLayout()
        self._scale_slider = QSlider(Qt.Horizontal)
        self._scale_slider.setRange(50, 200)
        self._scale_slider.setTickPosition(QSlider.TicksBelow)
        self._scale_slider.setTickInterval(10)
        self._scale_slider.valueChanged.connect(
            lambda v: self._scale_label.setText(f"{v}%")
        )
        scale_row.addWidget(self._scale_slider, 1)
        self._scale_label = QLabel("100%")
        self._scale_label.setMinimumWidth(80)
        self._scale_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._scale_label.setStyleSheet("color:#D4607F;font-weight:bold;font-size:14px;")
        scale_row.addWidget(self._scale_label)
        win_form.addRow("角色大小:", scale_row)

        hint = QLabel("◈ 基础 400×600 · 50% = 200×300 · 200% = 800×1200")
        hint.setStyleSheet("color:#B090A0;font-size:11px;padding-left:4px;")
        win_form.addRow("", hint)

        self._screen_combo = QComboBox()
        for i, s in enumerate(QApplication.screens()):
            g = s.geometry()
            self._screen_combo.addItem(
                f"🖥  {s.name() or f'屏幕 {i+1}'}  ({g.width()}×{g.height()})", i
            )
        win_form.addRow("显示器:", self._screen_combo)

        self._topmost_cb = QCheckBox("✦ 保持窗口置顶")
        win_form.addRow(self._topmost_cb)
        self._click_through_cb = QCheckBox("✦ 鼠标穿透模式")
        win_form.addRow(self._click_through_cb)
        win_layout.addStretch()
        self._tabs.addTab(win_page, "🌸 窗口")

        # ===== 🎀 角色 =====
        char_page = QWidget()
        char_layout = QVBoxLayout(char_page)
        char_layout.setSpacing(8)
        char_form = QFormLayout()
        char_form.setSpacing(8)
        char_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        char_layout.addLayout(char_form)
        self._model_combo = QComboBox()
        self._model_combo.addItems(["hiyori — 小日和"])
        self._model_combo.setEditable(True)
        self._model_combo.setInsertPolicy(QComboBox.NoInsert)
        char_form.addRow("当前模型:", self._model_combo)
        info = QGroupBox("📋 模型信息")
        info_layout = QVBoxLayout(info)
        info_layout.setSpacing(4)
        for txt in ["hiyori_pro_t11 (Live2D Cubism 4)",
                     "尺寸: 2976×4175 px  ·  10 个动作组",
                     "目录: models/hiyori/runtime/"]:
            lbl = QLabel(txt)
            lbl.setStyleSheet("color:#5A4060;font-size:11px;padding:2px 0;")
            info_layout.addWidget(lbl)
        char_layout.addWidget(info)
        char_layout.addStretch()
        self._tabs.addTab(char_page, "🎀 角色")

        # ===== ✨ 行为 =====
        beh_page = QWidget()
        beh_layout = QVBoxLayout(beh_page)
        beh_layout.setSpacing(8)
        beh_form = QFormLayout()
        beh_form.setSpacing(8)
        beh_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        beh_layout.addLayout(beh_form)
        self._hourly_chime_cb = QCheckBox("✦ 整点报时（8:00 ~ 22:00）")
        beh_form.addRow(self._hourly_chime_cb)

        idle_g = QGroupBox("💤 空闲行为")
        idle_l = QVBoxLayout(idle_g)
        idle_l.setSpacing(3)
        for emoji, t in [("🌿", "60秒: 轻闲发呆"), ("🌀", "3分钟: 开始无聊"),
                          ("🥱", "5分钟: 打哈欠"), ("😴", "10分钟: 打瞌睡"),
                          ("💤", "15分钟: 睡着 Zzz...")]:
            lbl = QLabel(f"{emoji}  {t}")
            lbl.setStyleSheet("color:#5A4060;font-size:11px;padding:2px 0;")
            idle_l.addWidget(lbl)
        beh_layout.addWidget(idle_g)

        mon_g = QGroupBox("📊 系统监控")
        mon_l = QVBoxLayout(mon_g)
        mon_l.setSpacing(3)
        for emoji, t in [("🔥", "CPU > 80% / 内存 > 85% 提醒"),
                          ("🔋", "电池 < 20% 且未充电 → 提醒充电"),
                          ("🔗", "剪贴板链接检测")]:
            lbl = QLabel(f"{emoji}  {t}")
            lbl.setStyleSheet("color:#5A4060;font-size:11px;padding:2px 0;")
            mon_l.addWidget(lbl)
        beh_layout.addWidget(mon_g)
        beh_layout.addStretch()
        self._tabs.addTab(beh_page, "✨ 行为")

        # ===== 🌤 天气 =====
        w_page = QWidget()
        w_layout = QVBoxLayout(w_page)
        w_layout.setSpacing(8)
        w_form = QFormLayout()
        w_form.setSpacing(8)
        w_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        w_layout.addLayout(w_form)
        self._weather_enabled_cb = QCheckBox("✦ 启动时自动播报天气")
        w_form.addRow(self._weather_enabled_cb)
        self._weather_city = QComboBox()
        self._weather_city.setEditable(True)
        self._weather_city.setInsertPolicy(QComboBox.NoInsert)
        self._weather_city.setMinimumWidth(280)
        for label, _ in _COMMON_CITIES:
            self._weather_city.addItem(label)
        self._weather_city.lineEdit().setPlaceholderText("输入城市英文/拼音名，如 beijing")
        w_form.addRow("城市:", self._weather_city)
        w_hint = QLabel("💡 支持国内外城市，输入英文名即可\n    例: beijing / tokyo / london / new york")
        w_hint.setStyleSheet("color:#B090A0;font-size:11px;padding:2px 0;")
        w_form.addRow("", w_hint)
        w_layout.addStretch()
        self._tabs.addTab(w_page, "🌤 天气")

        # ===== ⏰ 提醒 =====
        r_page = QWidget()
        r_layout = QVBoxLayout(r_page)
        r_layout.setSpacing(8)
        r_form = QFormLayout()
        r_form.setSpacing(8)
        r_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        r_layout.addLayout(r_form)
        self._reminder_enabled_cb = QCheckBox("✦ 启用定时提醒")
        r_form.addRow(self._reminder_enabled_cb)
        self._reminder_interval = QSpinBox()
        self._reminder_interval.setRange(5, 180)
        self._reminder_interval.setSuffix(" 分钟")
        self._reminder_interval.setValue(30)
        r_form.addRow("提醒间隔:", self._reminder_interval)
        self._reminder_text = QComboBox()
        self._reminder_text.setEditable(True)
        self._reminder_text.setInsertPolicy(QComboBox.NoInsert)
        self._reminder_text.addItems([
            "该起来活动一下啦~ 坐久了对身体不好哦",
            "喝点水吧，保持水分很重要！",
            "休息一下眼睛，看看远处~",
            "该起来走走啦！",
            "主人别忘记吃饭哦~",
            "做做伸展运动怎么样？",
        ])
        self._reminder_text.lineEdit().setPlaceholderText("输入自定义提醒内容")
        r_form.addRow("提醒内容:", self._reminder_text)
        r_layout.addStretch()
        self._tabs.addTab(r_page, "⏰ 提醒")

        # ---- 底部按钮 ----
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(
            "QPushButton{background:#F0E0E8;color:#8B5F7F;border-radius:8px;"
            "padding:8px 28px;font-size:13px;font-weight:bold;}"
            "QPushButton:hover{background:#E8D0DC;}"
            "QPushButton:pressed{background:#DCC0CE;}"
        )
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("✓  保存")
        save_btn.setStyleSheet(
            "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #E87EA0,stop:1 #D4607F);color:#fff;border-radius:8px;"
            "padding:8px 32px;font-size:13px;font-weight:bold;}"
            "QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #F090B0,stop:1 #E07090);}"
            "QPushButton:pressed{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #D07090,stop:1 #C06080);}"
        )
        save_btn.clicked.connect(self._save)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        main_layout.addLayout(btn_row)

    def _load_values(self):
        cfg = self._config
        s = int(cfg.get("window", "scale", default=1.0) * 100)
        self._scale_slider.setValue(s)
        self._scale_label.setText(f"{s}%")
        si = cfg.get("window", "screen_index", default=0)
        if si < self._screen_combo.count():
            self._screen_combo.setCurrentIndex(si)
        self._topmost_cb.setChecked(cfg.get("window", "topmost", default=True))
        self._click_through_cb.setChecked(cfg.get("window", "click_through", default=False))

        model = cfg.get("character", "current_model", default="hiyori")
        for i in range(self._model_combo.count()):
            if model in self._model_combo.itemText(i):
                self._model_combo.setCurrentIndex(i)
                break

        self._hourly_chime_cb.setChecked(cfg.get("behavior", "hourly_chime", default=True))
        self._weather_enabled_cb.setChecked(cfg.get("weather", "enabled", default=True))

        cur_city = cfg.get("weather", "city", default="beijing")
        found = False
        for i in range(len(_COMMON_CITIES)):
            if _COMMON_CITIES[i][1] == cur_city:
                self._weather_city.setCurrentIndex(i)
                found = True
                break
        if not found:
            self._weather_city.setEditText(cur_city)

        self._reminder_enabled_cb.setChecked(cfg.get("reminder", "enabled", default=False))
        self._reminder_interval.setValue(cfg.get("reminder", "interval_minutes", default=30))
        rt = cfg.get("reminder", "custom_text", default="该起来活动一下啦~ 坐久了对身体不好哦")
        found = False
        for i in range(self._reminder_text.count()):
            if self._reminder_text.itemText(i) == rt:
                self._reminder_text.setCurrentIndex(i)
                found = True
                break
        if not found:
            self._reminder_text.setEditText(rt)

    def _save(self):
        cfg = self._config
        # 收集所有配置变更，单次批量写入 YAML
        scale = self._scale_slider.value() / 100.0
        updates = [
            (("window", "scale"), scale),
            (("window", "screen_index"), self._screen_combo.currentData()),
            (("window", "topmost"), self._topmost_cb.isChecked()),
            (("window", "click_through"), self._click_through_cb.isChecked()),
        ]
        m = self._model_combo.currentText()
        updates.append((("character", "current_model"), m.split("—")[0].strip()))
        updates.append((("behavior", "hourly_chime"), self._hourly_chime_cb.isChecked()))
        updates.append((("weather", "enabled"), self._weather_enabled_cb.isChecked()))
        ci = self._weather_city.currentIndex()
        if 0 <= ci < len(_COMMON_CITIES):
            updates.append((("weather", "city"), _COMMON_CITIES[ci][1] or ""))
        else:
            updates.append((("weather", "city"), self._weather_city.currentText().strip() or "beijing"))
        updates.append((("reminder", "enabled"), self._reminder_enabled_cb.isChecked()))
        updates.append((("reminder", "interval_minutes"), self._reminder_interval.value()))
        updates.append((("reminder", "custom_text"),
                        self._reminder_text.currentText().strip()
                        or "该起来活动一下啦~ 坐久了对身体不好哦"))

        cfg.set_many(updates)
        self.accept()
