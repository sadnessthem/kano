# -*- mode: python ; coding: utf-8 -*-
"""Kanban — 桌面 Live2D 看板娘 PyInstaller 打包配置"""

import sys
import os
import glob

block_cipher = None

# 项目根目录（spec 运行时目录）
root = os.getcwd()

# ── 兼容 Anaconda 的 Qt5 _conda 后缀 DLL ──────────────────
conda_lib_bin = os.path.join(sys.base_prefix, 'Library', 'bin')
_conda_dlls = []
if os.path.isdir(conda_lib_bin):
    _conda_dlls = [
        (f, '.')
        for f in glob.glob(os.path.join(conda_lib_bin, 'Qt5*_conda.dll'))
    ]
    # 也加入可能缺少的 liblzma, libbz2, ffi 等
    for extra in ('liblzma.dll', 'LIBBZ2.dll', 'ffi.dll'):
        p = os.path.join(conda_lib_bin, extra)
        if os.path.exists(p):
            _conda_dlls.append((p, '.'))

# ── Qt 平台插件（必需，否则 GUI 无法启动）────────────────
conda_plugins = os.path.join(sys.base_prefix, 'Library', 'plugins')
_qt_plugins = []
if os.path.isdir(conda_plugins):
    for dirpath, _, fnames in os.walk(conda_plugins):
        for f in fnames:
            if f.endswith('.dll'):
                rel = os.path.relpath(dirpath, conda_plugins)
                _qt_plugins.append((os.path.join(dirpath, f),
                                    os.path.join('PyQt5', 'Qt5', 'plugins', rel)))

a = Analysis(
    ['main.py'],
    pathex=[root, conda_lib_bin],
    binaries=_conda_dlls + _qt_plugins,
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
    runtime_hooks=[os.path.join(root, 'pyi_conda_rthook.py')],
    excludes=[
        'PyQt5.QtLocation',
        'PyQt5.QtMultimedia',
        'PyQt5.QtBluetooth',
        'PyQt5.QtNfc',
        'PyQt5.QtSensors',
        'PyQt5.QtSerialPort',
        'PyQt5.QtXmlPatterns',
        'PyQt5.Qt3D*',
        'IPython',
        'jupyter',
        'matplotlib',
        'notebook',
        'pandas',
        'scipy',
        'sympy',
        'Cython',
        'setuptools',
        'pip',
        'wheel',
    ],
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
    name='桌宠',
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
    icon=os.path.join(root, 'resources', 'icon.ico'),
)
