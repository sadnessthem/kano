"""Patch pixi-live2d-display.js to wrap Cubism 2 code in a conditional"""
with open('E:/python_important/WHATEVER/web/lib/pixi-live2d-display.js', 'r', encoding='utf-8') as f:
    c = f.read()

# Insert `if (window.Live2D) {` before the ZipLoader middleware registration
block_start_marker = 'Live2DFactory.live2DModelMiddlewares.unshift(ZipLoader.factory);'
assert block_start_marker in c, "block_start_marker not found!"

# Insert closing `}` before the Cubism 4 code starts
block_end_marker = '\n  const InvalidMotionQueueEntryHandleValue = -1;'
assert block_end_marker in c, "block_end_marker not found!"

# Do the replacements
c = c.replace(
    block_start_marker,
    'if (window.Live2D) {\n  ' + block_start_marker,
    1  # only first occurrence
)

c = c.replace(
    block_end_marker,
    '\n  }\n  ' + block_end_marker.strip(),
    1  # only first occurrence
)

with open('E:/python_important/WHATEVER/web/lib/pixi-live2d-display.js', 'w', encoding='utf-8') as f:
    f.write(c)

print("Patching complete!")
# Verify
verify_marker1 = 'if (window.Live2D) {\n  Live2DFactory.live2DModelMiddlewares.unshift'
verify_marker2 = '}\n  const InvalidMotionQueueEntryHandleValue = -1;'
assert verify_marker1 in c, "Failed to verify first patch!"
assert verify_marker2 in c, "Failed to verify second patch!"
print("Both patches verified OK")
