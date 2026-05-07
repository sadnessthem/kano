"""番茄钟 — 专注计时器"""

from PyQt5.QtCore import QObject, QTimer, pyqtSignal


class PomodoroTimer(QObject):
    """番茄钟计时器，支持工作和休息模式切换"""

    state_changed = pyqtSignal(str)   # "idle" / "working" / "break"
    tick = pyqtSignal(int, int)       # remaining_seconds, total_seconds
    finished = pyqtSignal(str)        # "working" 工作时结束 / "break" 休息结束

    def __init__(self, work_minutes: int = 25, break_minutes: int = 5, parent=None):
        super().__init__(parent)
        self._work_sec = work_minutes * 60
        self._break_sec = break_minutes * 60
        self._remaining = 0
        self._state = "idle"  # idle / working / break

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

    # ---- 属性 ----

    @property
    def state(self) -> str:
        return self._state

    @property
    def remaining_seconds(self) -> int:
        return self._remaining

    def format_time(self) -> str:
        """返回 MM:SS 格式的剩余时间"""
        m = self._remaining // 60
        s = self._remaining % 60
        return f"{m:02d}:{s:02d}"

    # ---- 控制 ----

    def start_work(self):
        """开始一个工作时段"""
        self._remaining = self._work_sec
        self._state = "working"
        self._timer.start()
        self.state_changed.emit("working")

    def start_break(self):
        """开始休息时段"""
        self._remaining = self._break_sec
        self._state = "break"
        self._timer.start()
        self.state_changed.emit("break")

    def pause(self):
        """暂停"""
        self._timer.stop()

    def resume(self):
        """恢复"""
        if self._state != "idle":
            self._timer.start()

    def reset(self):
        """重置到空闲状态"""
        self._timer.stop()
        self._remaining = 0
        self._state = "idle"
        self.state_changed.emit("idle")

    # ---- 内部 ----

    def _on_tick(self):
        self._remaining -= 1
        total = self._work_sec if self._state == "working" else self._break_sec
        self.tick.emit(self._remaining, total)
        if self._remaining <= 0:
            self._timer.stop()
            old = self._state
            self._state = "idle"
            self.finished.emit(old)
