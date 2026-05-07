"""插件加载器 — 扫描插件目录并动态加载"""

import importlib
import inspect
import os
import pkgutil

from PyQt5.QtCore import QObject, QTimer

from .base import PluginBase


class PluginLoader(QObject):
    """插件加载器：扫描 plugins/ 目录，加载所有合法插件"""

    def __init__(self, bridge, config, dialog_manager):
        super().__init__()
        self._bridge = bridge
        self._config = config
        self._dialog = dialog_manager
        self._plugins = []       # type: list[PluginBase]
        self._tick_timers = []   # type: list[QTimer]

    def load_all(self, plugin_dir: str = None):
        """扫描并加载所有插件"""
        if plugin_dir is None:
            plugin_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "plugins"
            )

        count = 0
        for importer, modname, ispkg in pkgutil.iter_modules([plugin_dir]):
            if modname in ("base", "loader", "__init__"):
                continue
            try:
                module = importlib.import_module(f"plugins.{modname}")
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, PluginBase) and obj is not PluginBase
                            and not inspect.isabstract(obj)):
                        plugin = obj(self._bridge, self._config, self._dialog)
                        self._plugins.append(plugin)
                        plugin.on_load()
                        count += 1

                        # 设置 tick 定时器
                        if plugin.tick_interval > 0:
                            timer = QTimer(self)
                            timer.timeout.connect(plugin.on_tick)
                            timer.start(plugin.tick_interval * 1000)
                            self._tick_timers.append(timer)

                        print(f"[Plugins] Loaded: {plugin.name}")
            except Exception as e:
                print(f"[Plugins] Failed to load {modname}: {e}")

        print(f"[Plugins] Loaded {count} plugin(s)")
        return self._plugins

    def unload_all(self):
        """卸载所有插件"""
        for plugin in self._plugins:
            try:
                plugin.on_unload()
            except Exception as e:
                print(f"[Plugins] Unload error {plugin.name}: {e}")
        for timer in self._tick_timers:
            timer.stop()
        self._tick_timers.clear()
        self._plugins.clear()
        print("[Plugins] All plugins unloaded")

    def dispatch_event(self, event_type: str, data: dict):
        """向所有启用的插件分发事件"""
        for plugin in self._plugins:
            if plugin.enabled:
                try:
                    plugin.on_event(event_type, data)
                except Exception as e:
                    print(f"[Plugins] Event error {plugin.name}: {e}")

    @property
    def plugins(self) -> list:
        return list(self._plugins)
