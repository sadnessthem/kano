"""PyInstaller runtime hook: 修正 conda 环境下 Qt5 _conda DLL 加载路径"""
import os
import sys

# 打包后，_conda.dll 被复制到可执行文件所在目录
dll_dir = os.path.dirname(sys.executable)
if dll_dir not in os.environ.get('PATH', ''):
    os.environ['PATH'] = dll_dir + os.pathsep + os.environ.get('PATH', '')
