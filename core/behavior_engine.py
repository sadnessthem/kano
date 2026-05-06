"""行为引擎：时间感知、丰富交互、空闲行为、事件调度"""

import random
from PyQt5.QtCore import QObject, QTimer, QTime

from data.dialog_manager import DialogManager


class BehaviorEngine(QObject):
    """行为引擎：接收事件，决策角色行为，发送指令"""

    # 动作池
    CLICK_MOTIONS = ["Tap", "Tap@Body"]
    FLICK_MOTIONS = ["Flick", "FlickUp", "FlickDown"]
    IDLE_MOTIONS = ["Idle"]
    SPONTANEOUS_MOTIONS = ["Flick", "FlickUp", "Tap", "Idle"]

    def __init__(self, bridge, config, dialog_manager: DialogManager,
                 backend_services=None):
        super().__init__()
        self._bridge = bridge
        self._config = config
        self._dialog = dialog_manager
        self._backend = backend_services

        self._click_cooldown_time = QTime()
        self._greeting_done = False
        self._current_fps = 30  # 当前渲染帧率，避免重复发送

        # 随机自发动作定时器
        self._spontaneous_timer = QTimer(self)
        self._spontaneous_timer.timeout.connect(self._on_spontaneous)

        # 注册事件
        self._bridge.event_received.connect(self.handle_event)

        # 连接后端服务信号
        if self._backend:
            self._backend.idle_timeout.connect(self._on_idle_timeout)
            self._backend.return_from_idle.connect(self._on_return)
            self._backend.system_event.connect(self._on_system_event)
            self._backend.hourly_chime.connect(self._on_hourly_chime)
            self._backend.clipboard_url.connect(self._on_clipboard_url)
            self._backend.reminder_tick.connect(self._on_reminder_tick)
            self._backend.todo_tick.connect(self._on_todo_tick)

    # ====== 启动/停止 ======

    def start(self):
        """启动行为引擎"""
        self._start_spontaneous_timer()
        print("[Behavior] Engine started")

    def stop(self):
        """停止行为引擎"""
        self._spontaneous_timer.stop()

    def _start_spontaneous_timer(self):
        """启动随机自发动作定时器"""
        min_interval = self._config.get("behavior", "random_action_min_interval", default=30)
        self._schedule_spontaneous()

    def _schedule_spontaneous(self):
        """安排下一次自发动作"""
        min_s = self._config.get("behavior", "random_action_min_interval", default=30)
        max_s = self._config.get("behavior", "random_action_max_interval", default=90)
        interval = random.randint(min_s, max_s) * 1000
        self._spontaneous_timer.start(interval)

    # ====== 事件处理 ======

    def handle_event(self, event_type: str, data: dict):
        """处理来自 JS 桥的事件"""
        self._mark_interaction()

        handlers = {
            "frontend_ready": self._on_ready,
            "click": self._on_click,
            "double_click": self._on_double_click,
            "drag_end": self._on_drag_end,
            "mouse_enter": self._on_mouse_enter,
            "mouse_leave": self._on_mouse_leave,
        }
        handler = handlers.get(event_type)
        if handler:
            handler(data)

    def _mark_interaction(self):
        """通知后端服务有用户交互"""
        if self._backend:
            self._backend.mark_interaction()

    # ====== 就绪 ======

    def _on_ready(self, data: dict):
        """前端就绪 — 根据时间发送问候，可选播报天气"""
        print("[Behavior] Frontend ready — sending time-aware greeting")
        QTimer.singleShot(500, self._send_time_greeting)
        if self._config.get("weather", "auto_report_on_start", default=True):
            QTimer.singleShot(3000, self._auto_weather)

    def _auto_weather(self):
        """自动播报天气（问候之后）"""
        if self._backend and self._config.get("weather", "enabled", default=True):
            city = self._config.get("weather", "city", default="beijing")
            self._backend.weather_result.connect(self._on_weather_data)
            self._backend.fetch_weather(city)

    def _on_weather_data(self, city: str, data: dict):
        """异步天气数据到达"""
        self._backend.weather_result.disconnect(self._on_weather_data)
        if data:
            self.say_weather(data)

    def _send_time_greeting(self):
        """根据当前时间发送问候"""
        hour = QTime.currentTime().hour()
        if hour < 6:
            scene = "greeting_night"
            motion = "Flick"
        elif hour < 12:
            scene = "greeting_morning"
            motion = "Flick"
        elif hour < 14:
            scene = "greeting_noon"
            motion = "Flick"
        elif hour < 18:
            scene = "greeting_evening"
            motion = "Flick"
        else:
            scene = "greeting_night"
            motion = "Flick"

        dialog = self._dialog.get_dialog(scene)
        if dialog["text"]:
            self._bridge.send_command("showDialog", {
                "text": dialog["text"],
                "duration": dialog["duration"]
            })
            if dialog.get("emotion"):
                self._send_expression(dialog["emotion"])
        self._bridge.send_command("playMotion", {
            "group": motion,
            "index": 0,
            "priority": 2
        })
        self._greeting_done = True

        # 问候完后启动自发动作
        self._schedule_spontaneous()

    # ====== 点击交互 ======

    def _on_click(self, data: dict):
        """单击 — 随机对话 + 动作"""
        # 冷却检查（15秒）
        if self._click_cooldown_time.isValid() and self._click_cooldown_time.secsTo(QTime.currentTime()) < 15:
            return
        self._click_cooldown_time = QTime.currentTime()

        # 动作
        group = random.choice(self.CLICK_MOTIONS)
        self._bridge.send_command("playMotion", {
            "group": group, "index": 0, "priority": 3
        })

        # 台词
        dialog = self._dialog.get_dialog("click")
        if dialog["text"]:
            self._bridge.send_command("showDialog", {
                "text": dialog["text"], "duration": dialog["duration"]
            })
            if dialog.get("emotion"):
                self._send_expression(dialog["emotion"])

    def _on_double_click(self, data: dict):
        """双击 — 惊喜反应"""
        group = random.choice(self.FLICK_MOTIONS)
        self._bridge.send_command("playMotion", {
            "group": group, "index": 0, "priority": 3
        })
        dialog = self._dialog.get_dialog("double_click")
        if dialog["text"]:
            self._bridge.send_command("showDialog", {
                "text": dialog["text"], "duration": dialog["duration"]
            })
            if dialog.get("emotion"):
                self._send_expression(dialog["emotion"])

    def _on_drag_end(self, data: dict):
        """拖拽结束"""
        self._bridge.send_command("playMotion", {
            "group": "Tap@Body", "index": 0, "priority": 2
        })
        dialog = self._dialog.get_dialog("drag_end")
        if dialog["text"]:
            self._bridge.send_command("showDialog", {
                "text": dialog["text"], "duration": dialog["duration"]
            })
            if dialog.get("emotion"):
                self._send_expression(dialog["emotion"])

    # ====== 鼠标悬停 ======

    def _on_mouse_enter(self, data: dict):
        """鼠标进入角色区域"""
        dialog = self._dialog.get_dialog("mouse_enter")
        if dialog["text"]:
            self._bridge.send_command("showDialog", {
                "text": dialog["text"], "duration": dialog["duration"]
            })

    def _on_mouse_leave(self, data: dict):
        """鼠标离开角色区域"""
        # 简单动作表示注意到了
        pass

    # ====== 空闲行为 ======

    def _on_idle_timeout(self, level: int):
        """空闲超时 — 按等级触发不同行为"""
        scene_map = {1: "idle_level1", 2: "idle_level2", 3: "idle_level3", 4: "idle_level3", 5: "idle_level3"}
        scene = scene_map.get(level, "idle_level1")

        dialog = self._dialog.get_dialog(scene)
        if dialog["text"]:
            self._bridge.send_command("showDialog", {
                "text": dialog["text"], "duration": dialog["duration"]
            })
            if dialog.get("emotion"):
                self._send_expression(dialog["emotion"])

        # 空闲等级高时减速 FPS 以节省资源
        if level >= 3:
            self._bridge.send_command("playMotion", {
                "group": "Idle", "index": 0, "priority": 1
            })
            self._set_fps(15)
        elif level >= 1:
            self._set_fps(25)

    def _on_return(self):
        """用户回归"""
        dialog = self._dialog.get_dialog("return_from_idle")
        if dialog["text"]:
            self._bridge.send_command("showDialog", {
                "text": dialog["text"], "duration": dialog["duration"]
            })
            if dialog.get("emotion"):
                self._send_expression(dialog["emotion"])
        self._bridge.send_command("playMotion", {
            "group": "Flick", "index": 0, "priority": 3
        })
        # 恢复帧率
        self._set_fps(30)

    # ====== 系统事件 ======

    def _on_system_event(self, event_type: str, data: dict):
        """处理系统监控事件"""
        dialog = self._dialog.get_dialog(event_type, **data)
        if dialog["text"]:
            self._bridge.send_command("showDialog", {
                "text": dialog["text"], "duration": dialog["duration"]
            })
            if dialog.get("emotion"):
                self._send_expression(dialog["emotion"])

    # ====== 整点报时 ======

    def _on_hourly_chime(self, hour: int):
        """整点报时"""
        dialog = self._dialog.get_dialog("hourly_chime", hour=hour)
        if dialog["text"]:
            self._bridge.send_command("showDialog", {
                "text": dialog["text"], "duration": dialog["duration"]
            })
            self._bridge.send_command("playMotion", {
                "group": "Flick", "index": 0, "priority": 2
            })

    # ====== 自发动作 ======

    def _on_spontaneous(self):
        """随机自发动作 — 随机做动作、说台词、或表情"""
        self._mark_interaction()
        roll = random.random()

        if roll < 0.25:
            # 25%: 播放随机动作
            group = random.choice(self.SPONTANEOUS_MOTIONS)
            self._bridge.send_command("playMotion", {
                "group": group, "index": 0, "priority": 1
            })
        elif roll < 0.45:
            # 20%: 随机说句台词
            scenes = ["click", "idle_level1"]
            dialog = self._dialog.get_dialog(random.choice(scenes))
            if dialog["text"]:
                self._bridge.send_command("showDialog", {
                    "text": dialog["text"], "duration": dialog["duration"]
                })
        # 35%: 什么都不做（安静）

        # 安排下一次
        self._schedule_spontaneous()

    # ====== 剪贴板 URL ======

    def _on_clipboard_url(self, url: str):
        """剪贴板检测到 URL"""
        self._bridge.send_command("showDialog", {
            "text": f"主人复制了一个链接哦~\n{url[:40]}{'...' if len(url) > 40 else ''}",
            "duration": 5000
        })

    # ====== 定时提醒 ======

    def _on_reminder_tick(self):
        """定时提醒触发"""
        text = self._config.get("reminder", "custom_text", default="该起来活动一下啦~")
        self._bridge.send_command("showDialog", {
            "text": f"🔔 {text}",
            "duration": 4000
        })

    def _on_todo_tick(self, summary: str):
        """待办事项提醒"""
        self._bridge.send_command("showDialog", {
            "text": summary,
            "duration": 6000
        })

    # ====== 对话/天气 公共方法 ======

    def show_dialog(self, text: str, duration: int = 3000, emotion: str = None):
        """外部接口：显示对话气泡"""
        self._bridge.send_command("showDialog", {
            "text": text, "duration": duration
        })
        if emotion:
            self._send_expression(emotion)

    def say_weather(self, weather_data: dict):
        """播报天气"""
        if not weather_data or not weather_data.get("temp"):
            self._bridge.send_command("showDialog", {
                "text": "天气服务暂时不可用~", "duration": 3000
            })
            return
        dialog = self._dialog.get_dialog("weather_report", **weather_data)
        if dialog["text"]:
            self._bridge.send_command("showDialog", {
                "text": dialog["text"], "duration": dialog["duration"]
            })

    # ====== 性能控制 ======

    def _set_fps(self, fps: int):
        """设置渲染帧率（避免重复发送相同值）"""
        if fps != self._current_fps:
            self._current_fps = fps
            self._bridge.send_command("setFPS", {"fps": fps})

    # ====== 辅助 ======

    def _send_expression(self, emotion: str):
        """发送表情指令（如果前端支持）"""
        # 表情 ID 映射
        expr_map = {
            "smile": "smile",
            "happy": "happy",
            "surprise": "surprise",
            "sad": "sad",
            "neutral": "neutral",
        }
        expr_id = expr_map.get(emotion)
        if expr_id:
            self._bridge.send_command("setExpression", {"expression_id": expr_id})
