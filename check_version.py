"""检查 pixi-live2d-display 和 PixiJS 版本"""
import re

# Check pixi-live2d-display
with open('E:/python_important/WHATEVER/web/lib/pixi-live2d-display.js', 'r') as f:
    c = f.read()

# Find all version-like strings
for m in re.finditer(r'["\']version["\']\s*[:=]\s*["\']([^"\']+)["\']', c):
    print(f'Version string: {m.group(1)}')

# Check for Cubism 4 references
if 'cubism4' in c.lower():
    print('Contains cubism4 references')
if 'Cubism4' in c:
    print('Contains Cubism4 class')
if 'live2dcubismcore' in c.lower():
    print('Contains live2dcubismcore reference')

# Check for Cubism 2 references
if 'live2d.min.js' in c:
    print('Contains live2d.min.js reference')
if 'Cubism2' in c:
    print('Contains Cubism2 class reference')

# Look at the error message
idx = c.find('Could not find Cubism 2')
if idx >= 0:
    snippet = c[max(0,idx-100):idx+200]
    print(f'\nContext around Cubism 2 error:\n...{snippet}...')

# Check PixiJS version
with open('E:/python_important/WHATEVER/web/lib/pixi.min.js', 'r') as f:
    pixi = f.read(5000)
for m in re.finditer(r'pixi\.js\s+v?(\d+\.\d+\.\d+)', pixi, re.I):
    print(f'\nPixiJS version: {m.group(1)}')
if 'PIXI.Color' in pixi:
    print('PixiJS has Color class')
