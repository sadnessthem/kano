/**
 * interaction.js — 用户交互事件捕获
 *
 * 鼠标事件通过 QWebChannel Bridge 发送给 Python 端。
 * 拖拽功能完全在 JS 侧检测，通过 bridge 通知 Python 移动窗口。
 * （QWebEngineView 的鼠标事件被 Chromium 内部消费，Qt eventFilter 无法捕获）
 */

(function () {
    'use strict';

    var clickTimer = null;
    var isDragging = false;
    var mouseDownPos = { x: 0, y: 0 };
    var mouseDownTime = 0;
    var DRAG_THRESHOLD = 5;       // 拖拽判定阈值（像素）
    var DBL_CLICK_DELAY = 300;    // 双击判定时间（ms）

    var container = document.getElementById('role-container');
    if (!container) return;

    // ---- 鼠标进入/离开 ----
    container.addEventListener('mouseenter', function (e) {
        if (typeof sendEvent === 'function') {
            sendEvent('mouse_enter', { x: e.clientX, y: e.clientY });
        }
    });

    container.addEventListener('mouseleave', function (e) {
        if (typeof sendEvent === 'function') {
            sendEvent('mouse_leave', { x: e.clientX, y: e.clientY });
        }
    });

    // ---- 鼠标按下 ----
    container.addEventListener('mousedown', function (e) {
        mouseDownPos = { x: e.screenX, y: e.screenY };
        mouseDownTime = Date.now();
        isDragging = false;
    });

    // ---- 鼠标移动（拖拽检测） ----
    container.addEventListener('mousemove', function (e) {
        if (e.buttons === 0) return;  // 未按下左键

        var currentX = e.screenX;
        var currentY = e.screenY;
        var dx = currentX - mouseDownPos.x;
        var dy = currentY - mouseDownPos.y;
        var dist = Math.sqrt(dx * dx + dy * dy);

        if (dist > DRAG_THRESHOLD) {
            if (!isDragging) {
                // 开始拖拽
                isDragging = true;
                if (typeof sendEvent === 'function') {
                    sendEvent('drag_start', {
                        mouseX: currentX,
                        mouseY: currentY
                    });
                }
            } else {
                // 拖拽进行中
                if (typeof sendEvent === 'function') {
                    sendEvent('drag_move', {
                        mouseX: currentX,
                        mouseY: currentY
                    });
                }
            }
        }
    });

    // ---- 鼠标释放 ----
    container.addEventListener('mouseup', function (e) {
        if (isDragging) {
            // 拖拽结束
            if (typeof sendEvent === 'function') {
                sendEvent('drag_end', {});
            }
            isDragging = false;
            return;
        }

        // 非拖拽 → 单击/双击判定
        if (clickTimer) {
            // 第二次点击 → 判定为双击
            clearTimeout(clickTimer);
            clickTimer = null;
            if (typeof sendEvent === 'function') {
                sendEvent('double_click', {
                    x: e.clientX,
                    y: e.clientY
                });
            }
        } else {
            // 第一次点击 → 等待双击判定
            clickTimer = setTimeout(function () {
                clickTimer = null;
                if (!isDragging && typeof sendEvent === 'function') {
                    sendEvent('click', {
                        x: e.clientX,
                        y: e.clientY
                    });
                }
            }, DBL_CLICK_DELAY);
        }
    });

    // ---- 右键菜单（阻止浏览器默认菜单） ----
    container.addEventListener('contextmenu', function (e) {
        e.preventDefault();
    });

})();
