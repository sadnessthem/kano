# -*- mode: python ; coding: utf-8 -*-
"""Kanban — 桌面 Live2D 看板娘 PyInstaller 打包配置"""

import sys
import os

block_cipher = None

# 项目根目录
root = os.path.dirname(os.path.abspath(__file__))

a = Analysis(
    ['main.py'],
    pathex=[root],
    binaries=[],
    datas=[
        # 前端页面
        (os.path.join(root, 'web', 'index.html'), 'web'),
        (os.path.join(root, 'web', 'css'), 'web/css'),
        (os.path.join(root, 'web', 'js'), 'web/js'),
        # 前端库
        (os.path.join(root, 'web', 'lib', 'live2dcubismcore.min.js'), 'web/lib'),
        (os.path.join(root, 'web', 'lib', 'pixi.min.js'), 'web/lib'),
        (os.path.join(root, 'web', 'lib', 'pixi-live2d-display.js'), 'web/lib'),
        # 模型
        (os.path.join(root, 'models'), 'models'),
        # 台词包
        (os.path.join(root, 'data', 'dialogs_zh_CN.json'), 'data'),
        # 图标
        (os.path.join(root, 'resources', 'icon.svg'), 'resources'),
    ],
    hiddenimports=[
        'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtWebChannel',
        'PyQt5.QtWebEngine',
        'PyQt5.QtNetwork',
        'psutil',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Kanban',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # 可替换为 .ico 文件
)
