"""配置管理器：YAML 配置文件的读写和校验"""

import os
import yaml

DEFAULT_CONFIG = {
    "app": {
        "language": "zh_CN",
        "start_on_boot": False
    },
    "window": {
        "scale": 1.0,
        "position": {"x": None, "y": None},
        "topmost": True,
        "click_through": False,
        "screen_index": 0,
        "edge_snap": True,
        "mini_mode": False
    },
    "character": {
        "current_model": "hiyori",
        "models_path": "./models/"
    },
    "behavior": {
        "idle_thresholds": {
            "level1": 60,
            "level2": 180,
            "level3": 300,
            "level4": 600,
            "level5": 900
        },
        "random_action_min_interval": 30,
        "random_action_max_interval": 90,
        "mouse_follow": True,
        "hourly_chime": True,
        "hourly_chime_start": 8,
        "hourly_chime_end": 22
    },
    "dialog": {
        "enabled": True,
        "typing_speed_ms": 50,
        "display_duration_ms": 3000,
        "max_length": 40
    },
    "system_monitor": {
        "enabled": True,
        "cpu_threshold": 80,
        "memory_threshold": 85,
        "battery_threshold": 20,
        "check_interval_seconds": 10,
        "cpu_alert_cooldown_minutes": 5,
        "battery_alert_cooldown_minutes": 5
    },
    "weather": {
        "city": "beijing",
        "enabled": True,
        "auto_report_on_start": True
    },
    "reminder": {
        "enabled": False,
        "interval_minutes": 30,
        "custom_text": "该起来活动一下啦~"
    },
    "clipboard": {
        "enabled": True,
        "url_detection": True
    }
}


class ConfigManager:
    """管理 YAML 配置文件的读写，提供默认值和类型校验"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config.yaml"
        )
        self._config = None
        self._load()

    def _load(self):
        """加载配置，文件不存在则生成默认配置"""
        if not os.path.exists(self.config_path):
            self._config = DEFAULT_CONFIG.copy()
            self.save()
        else:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
            # 合并默认值（补全新添加的字段）
            self._merge_defaults()

    def _merge_defaults(self):
        """递归合并默认配置，确保新版本新增的字段不会缺失"""
        def _merge(target, default):
            for key, val in default.items():
                if key not in target:
                    target[key] = val
                elif isinstance(val, dict) and isinstance(target[key], dict):
                    _merge(target[key], val)
        _merge(self._config, DEFAULT_CONFIG)

    def save(self):
        """保存当前配置到文件"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)

    def get(self, *keys, default=None):
        """安全地按路径读取配置项，如 config.get('window', 'scale')"""
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
        return value if value is not None else default

    def set(self, *args):
        """设置配置值，最后两个参数为 key 序列和 value
        用法：config.set('window', 'scale', 1.5)
        """
        *keys, value = args
        target = self._config
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value
        self.save()

    def set_many(self, updates: list):
        """批量设置多项配置，只保存一次文件
        用法：config.set_many([
            (('window', 'scale'), 1.5),
            (('window', 'topmost'), True),
        ])
        """
        for keys, value in updates:
            target = self._config
            for key in keys[:-1]:
                if key not in target:
                    target[key] = {}
                target = target[key]
            target[keys[-1]] = value
        self.save()

    @property
    def raw(self) -> dict:
        return self._config
