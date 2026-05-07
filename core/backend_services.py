"""后端服务：空闲检测、系统监控、整点报时、天气查询、剪贴板、提醒"""

import psutil
import json
import re
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QTime, QUrl
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt5.QtWidgets import QApplication


class BackendServices(QObject):
    """聚合后端服务，通过信号与 BehaviorEngine 通信"""

    idle_timeout = pyqtSignal(int)        # 空闲等级 1-5
    return_from_idle = pyqtSignal()       # 用户回归
    system_event = pyqtSignal(str, dict)  # 事件类型, 数据
    hourly_chime = pyqtSignal(int)        # 当前小时数
    clipboard_url = pyqtSignal(str)       # 剪贴板检测到 URL
    reminder_tick = pyqtSignal()          # 定时提醒
    todo_tick = pyqtSignal(str)           # 待办提醒文本摘要
    weather_result = pyqtSignal(str, dict)  # city, data（异步天气结果）

    def __init__(self, config):
        super().__init__()
        self._config = config
        self._cfg = config.raw.get("behavior", {})
        self._sys_cfg = config.raw.get("system_monitor", {})
        self._clip_cfg = config.raw.get("clipboard", {})
        self._rem_cfg = config.raw.get("reminder", {})

        # 空闲追踪
        self._last_interaction = QTime.currentTime()
        self._idle_level = 0
        self._was_idle = False

        # 系统监控冷却
        self._cpu_last_alert = QTime()
        self._battery_last_alert = QTime()

        # 整点追踪
        self._last_hour = -1

        # 剪贴板追踪（避免重复触发）
        self._last_clip_text = ""

        # 定时器
        self._idle_timer = QTimer(self)
        self._monitor_timer = QTimer(self)
        self._chime_timer = QTimer(self)
        self._reminder_timer = QTimer(self)
        self._todo_timer = QTimer(self)

        # 待办管理器
        self._todo_manager = None

        # 天气缓存
        self._weather_cache = {}
        self._weather_city = config.get("weather", "city", default="beijing")

        # 异步网络管理器
        self._network = QNetworkAccessManager(self)

    def set_todo_manager(self, manager):
        """注入 TodoManager 实例"""
        self._todo_manager = manager

    def start_all(self):
        """按配置启动各后台服务"""
        # 空闲检测始终开启（行为引擎依赖）
        self._idle_timer.timeout.connect(self._check_idle)
        self._idle_timer.start(10000)

        if self._sys_cfg.get("enabled", True):
            self._monitor_timer.timeout.connect(self._check_system)
            self._monitor_timer.start(
                max(5000, self._sys_cfg.get("check_interval_seconds", 10) * 1000)
            )

        if self._cfg.get("hourly_chime", True):
            self._chime_timer.timeout.connect(self._check_hourly_chime)
            self._chime_timer.start(30000)

        if self._clip_cfg.get("enabled", True):
            QApplication.clipboard().dataChanged.connect(self._on_clipboard_change)

        if self._rem_cfg.get("enabled", False):
            self._start_reminder()

        # 待办检查（每 60 秒检查一次逾期/提醒）
        if self._todo_manager is not None:
            self._todo_timer.timeout.connect(self._check_todos)
            self._todo_timer.start(60000)

        print("[Services] All services started")

    def stop_all(self):
        """停止所有后台服务"""
        self._idle_timer.stop()
        self._monitor_timer.stop()
        self._chime_timer.stop()
        self._reminder_timer.stop()
        self._todo_timer.stop()

        try:
            QApplication.clipboard().dataChanged.disconnect(self._on_clipboard_change)
        except TypeError:
            pass

        print("[Services] All services stopped")

    def _check_todos(self):
        """检查待办事项，触发提醒"""
        if self._todo_manager is None:
            return
        # 到期提醒
        due = self._todo_manager.get_due()
        for item in due:
            self.todo_tick.emit(f"⏰ 待办到期: {item.text}")
        # 预提醒
        needs = self._todo_manager.get_needs_remind()
        for item in needs:
            self.todo_tick.emit(f"📌 待办提醒: {item.text}")

    def query_todo_summary(self) -> str:
        """获取待办摘要（供菜单/行为引擎调用）"""
        if self._todo_manager is None:
            return "待办服务暂未启用~"
        return self._todo_manager.summary()

    def restart_service(self, name: str):
        """运行时重启单个服务（从 config 重新读取后重启）
        name: 'monitor' | 'chime' | 'clipboard' | 'reminder'
        """
        self.stop_service(name)
        self._refresh_config_refs()
        self.start_service(name)

    def start_service(self, name: str):
        """单独启动一个后台服务"""
        if name == "monitor" and self._sys_cfg.get("enabled", True):
            self._monitor_timer.timeout.connect(self._check_system)
            self._monitor_timer.start(
                max(5000, self._sys_cfg.get("check_interval_seconds", 10) * 1000)
            )
        elif name == "chime" and self._cfg.get("hourly_chime", True):
            self._chime_timer.timeout.connect(self._check_hourly_chime)
            self._chime_timer.start(30000)
        elif name == "clipboard" and self._clip_cfg.get("enabled", True):
            QApplication.clipboard().dataChanged.connect(self._on_clipboard_change)
        elif name == "reminder" and self._rem_cfg.get("enabled", False):
            self._start_reminder()

    def stop_service(self, name: str):
        """单独停止一个后台服务"""
        if name == "monitor":
            self._monitor_timer.stop()
            try:
                self._monitor_timer.timeout.disconnect(self._check_system)
            except TypeError:
                pass
        elif name == "chime":
            self._chime_timer.stop()
            try:
                self._chime_timer.timeout.disconnect(self._check_hourly_chime)
            except TypeError:
                pass
        elif name == "clipboard":
            try:
                QApplication.clipboard().dataChanged.disconnect(self._on_clipboard_change)
            except TypeError:
                pass
        elif name == "reminder":
            self._reminder_timer.stop()
            try:
                self._reminder_timer.timeout.disconnect(self._on_reminder)
            except TypeError:
                pass

    def _refresh_config_refs(self):
        """运行时重新读取所有配置引用"""
        self._cfg = self._config.raw.get("behavior", {})
        self._sys_cfg = self._config.raw.get("system_monitor", {})
        self._clip_cfg = self._config.raw.get("clipboard", {})
        self._rem_cfg = self._config.raw.get("reminder", {})

    # ====== 用户互动标记 ======

    def mark_interaction(self):
        """标记用户有交互"""
        self._last_interaction = QTime.currentTime()
        if self._was_idle:
            self._was_idle = False
            self._idle_level = 0
            self.return_from_idle.emit()

    # ====== 空闲检测 ======

    def _check_idle(self):
        """检查空闲时长，按等级触发"""
        thresholds = self._cfg.get("idle_thresholds", {})
        elapsed = self._last_interaction.secsTo(QTime.currentTime())

        level = 0
        if elapsed >= thresholds.get("level5", 900):
            level = 5
        elif elapsed >= thresholds.get("level4", 600):
            level = 4
        elif elapsed >= thresholds.get("level3", 300):
            level = 3
        elif elapsed >= thresholds.get("level2", 180):
            level = 2
        elif elapsed >= thresholds.get("level1", 60):
            level = 1

        if level > 0 and level != self._idle_level:
            self._idle_level = level
            self._was_idle = True
            self.idle_timeout.emit(level)
        elif level == 0 and self._idle_level > 0:
            self._idle_level = 0

    # ====== 系统监控 ======

    def _check_system(self):
        if not self._sys_cfg.get("enabled", True):
            return
        try:
            cpu = psutil.cpu_percent(interval=0)
            threshold = self._sys_cfg.get("cpu_threshold", 80)
            cooldown = self._sys_cfg.get("cpu_alert_cooldown_minutes", 5)
            if cpu >= threshold and self._cpu_last_alert.secsTo(QTime.currentTime()) > cooldown * 60:
                self._cpu_last_alert = QTime.currentTime()
                self.system_event.emit("cpu_alert", {"cpu": cpu, "threshold": threshold})
        except Exception:
            pass
        try:
            mem = psutil.virtual_memory()
            threshold = self._sys_cfg.get("memory_threshold", 85)
            if mem.percent >= threshold:
                self.system_event.emit("memory_alert", {"memory": mem.percent, "threshold": threshold})
        except Exception:
            pass
        try:
            battery = psutil.sensors_battery()
            if battery is not None:
                threshold = self._sys_cfg.get("battery_threshold", 20)
                cooldown = self._sys_cfg.get("battery_alert_cooldown_minutes", 5)
                if battery.percent <= threshold and not battery.power_plugged \
                        and self._battery_last_alert.secsTo(QTime.currentTime()) > cooldown * 60:
                    self._battery_last_alert = QTime.currentTime()
                    self.system_event.emit("battery_low", {"battery": battery.percent, "threshold": threshold})
        except Exception:
            pass

    # ====== 整点报时 ======

    def _check_hourly_chime(self):
        if not self._cfg.get("hourly_chime", True):
            return
        now = QTime.currentTime()
        hour = now.hour()
        start = self._cfg.get("hourly_chime_start", 8)
        end = self._cfg.get("hourly_chime_end", 22)
        if hour < start or hour >= end:
            self._last_hour = -1
            return
        if hour != self._last_hour and now.minute() == 0 and now.second() < 30:
            self._last_hour = hour
            self.hourly_chime.emit(hour)

    # ====== 剪贴板监控 ======

    def _on_clipboard_change(self):
        """检测剪贴板内容变化，识别 URL"""
        if not self._clip_cfg.get("url_detection", True):
            return
        try:
            text = QApplication.clipboard().text().strip()
            if not text or text == self._last_clip_text:
                return
            self._last_clip_text = text
            # 检测 URL 模式
            url_pattern = re.compile(
                r'https?://[^\s<>"\'(){}|\\^`[\]]+',
                re.IGNORECASE
            )
            match = url_pattern.search(text)
            if match:
                self.clipboard_url.emit(match.group(0))
        except Exception:
            pass

    # ====== 定时提醒 ======

    def _start_reminder(self):
        """启动定时提醒（幂等）"""
        try:
            self._reminder_timer.timeout.disconnect(self._on_reminder)
        except TypeError:
            pass
        interval = max(5, self._rem_cfg.get("interval_minutes", 30)) * 60 * 1000
        self._reminder_timer.timeout.connect(self._on_reminder)
        self._reminder_timer.start(interval)

    def restart_reminder(self):
        """运行时重新配置提醒（从 config 读取最新值后重启定时器）"""
        self._rem_cfg = self._config.raw.get("reminder", {})
        enabled = self._rem_cfg.get("enabled", False)
        if enabled:
            self._start_reminder()
        else:
            self._reminder_timer.stop()

    def _on_reminder(self):
        """定时提醒触发"""
        self.reminder_tick.emit()

    # ====== 天气查询（异步，不阻塞 UI） ======

    def fetch_weather(self, city: str = None):
        """异步查询天气，结果通过 weather_result 信号返回"""
        if city:
            self._weather_city = city
        if not self._weather_city or not self._weather_city.strip():
            self.weather_result.emit(self._weather_city, {})
            return
        # 检查缓存（5分钟内有效）
        if self._weather_city in self._weather_cache:
            import time
            cached = self._weather_cache[self._weather_city]
            if time.time() - cached.get("_time", 0) < 300:
                self.weather_result.emit(self._weather_city, cached)
                return
        # 异步请求
        city_clean = self._weather_city.strip().lower()
        url = f"https://wttr.in/{city_clean}?format=j1"
        req = QNetworkRequest(QUrl(url))
        req.setHeader(QNetworkRequest.UserAgentHeader, "Kanban/1.0")
        reply = self._network.get(req)
        reply.finished.connect(lambda r=reply: self._on_weather_reply(r, self._weather_city))

    def _on_weather_reply(self, reply, city: str):
        """处理异步天气响应"""
        try:
            if reply.error():
                print(f"[Services] Weather HTTP error: {reply.error()}")
                cached = self._weather_cache.get(city)
                if cached:
                    self.weather_result.emit(city, cached)
                return
            data = json.loads(bytes(reply.readAll()).decode("utf-8"))
            current = data["current_condition"][0]
            temp_c = int(current["temp_C"])
            desc = current["weatherDesc"][0]["value"]
            humidity = current["humidity"]
            wind = current["windspeedKmph"]
            result = {
                "temp": f"{temp_c}°C",
                "condition": desc,
                "humidity": f"{humidity}%",
                "wind": f"{wind}km/h",
                "advice": self._weather_advice(temp_c, desc),
                "_time": __import__("time").time(),
            }
            self._weather_cache[city] = result
            self.weather_result.emit(city, result)
        except Exception as e:
            print(f"[Services] Weather parse error: {e}")
            cached = self._weather_cache.get(city)
            if cached:
                self.weather_result.emit(city, cached)

    @staticmethod
    def _weather_advice(temp: int, desc: str) -> str:
        desc_lower = desc.lower()
        if "rain" in desc_lower or "drizzle" in desc_lower:
            return "记得带伞哦~"
        if "snow" in desc_lower:
            return "下雪了，注意保暖！"
        if "thunder" in desc_lower or "storm" in desc_lower:
            return "有雷暴，注意安全！"
        if temp >= 35:
            return "好热！注意防暑~"
        if temp >= 30:
            return "天气有点热，多喝水~"
        if temp <= 0:
            return "零下了！多加件衣服！"
        if temp <= 10:
            return "天气有点冷，注意保暖~"
        return "天气不错，适合出门走走~"
