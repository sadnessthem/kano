/**
 * bridge.js — JS 端通信桥
 *
 * 通过 QWebChannel 与 Python 双向通信
 * Python → JS: window.receiveCommand(cmd)
 * JS → Python: bridge.handle_js_event(jsonStr)
 */

// QWebChannel 连接成功后的回调
let bridge = null;

function initBridge() {
    new QWebChannel(qt.webChannelTransport, function (channel) {
        bridge = channel.objects.bridge;
        console.log('[Bridge] QWebChannel connected');

        // 通知 Python：前端已就绪
        sendEvent('frontend_ready', {});
    });
}

/**
 * 接收从 Python 发来的命令
 * @param {Object} cmd - { type: 'command', action: '...', params: {...} }
 */
window.receiveCommand = function (cmd) {
    console.log('[Bridge] Command received:', cmd.action, cmd.params);
    const handlers = {
        'playMotion': (p) => player.playMotion(p),
        'setExpression': (p) => player.setExpression(p),
        'showDialog': (p) => dialog.show(p),
        'setScale': (p) => setScaleHandler(p),
        'setFPS': (p) => setFPSHandler(p),
        'setDraggable': (p) => setDraggableHandler(p),
        'setMiniMode': (p) => setMiniModeHandler(p),
        'reload': (p) => reloadHandler(p),
    };

    const handler = handlers[cmd.action];
    if (handler) {
        handler(cmd.params || {});
    } else {
        console.warn('[Bridge] Unknown command:', cmd.action);
    }
};

/**
 * 向 Python 发送事件
 * @param {string} eventType - 事件类型
 * @param {Object} data - 附加数据
 */
function sendEvent(eventType, data) {
    if (!bridge) return;
    const payload = JSON.stringify({
        type: 'event',
        event: eventType,
        data: data || {},
        timestamp: Date.now()
    });
    bridge.handle_js_event(payload);
}

// ---- 命令处理器 ----

function setScaleHandler(params) {
    if (window.live2dApp) {
        window.live2dApp.stage.scale.set(params.scale);
    }
}

function setFPSHandler(params) {
    if (window.live2dApp && params.fps) {
        window.live2dApp.ticker.maxFPS = params.fps;
        if (params.fps <= 15) {
            window.live2dApp.ticker.autoStart = false;
            window.live2dApp.ticker.start();
            // 空闲时降低帧率后隔几帧停 ticker 更省资源
            var frameCount = 0;
            var cb = function() {
                frameCount++;
                if (frameCount > 60) {
                    window.live2dApp.ticker.remove(cb);
                }
            };
            window.live2dApp.ticker.add(cb);
        }
    }
}

// ---- 迷你模式状态（供 resize 事件使用） ----
var _miniModeActive = false;

function setMiniModeHandler(params) {
    _miniModeActive = params.enable;
    if (!window.live2dModel || !window.live2dApp) return;
    _applyMiniMode();
}

function _applyMiniMode() {
    if (!window.live2dModel || !window.live2dApp) return;
    if (_miniModeActive) {
        // 保存原始缩放比例（首次进入时）
        if (window._normalScale === undefined) {
            window._normalScale = window.live2dModel.scale.x;
        }
        // 放大模型使头部填满小窗口
        var zoom = 3;
        window.live2dModel.scale.set(window._normalScale * zoom, window._normalScale * zoom);
        // 动态计算偏移量：模型顶部对齐视口顶部，留30px边距
        // model.height 已包含当前缩放，即缩放后的像素高度
        var modelH = window.live2dModel.height;
        window.live2dModel.position.set(0, modelH - window.innerHeight + 30);
        window.live2dApp.stage.y = window.innerHeight;
        window.live2dApp.stage.x = window.innerWidth / 2;
    } else {
        // 恢复正常
        if (window._normalScale !== undefined) {
            window.live2dModel.scale.set(window._normalScale, window._normalScale);
        }
        window.live2dModel.position.set(0, 0);
        window.live2dApp.stage.y = window.innerHeight;
        window.live2dApp.stage.x = window.innerWidth / 2;
    }
}

function setDraggableHandler(params) {
    // 拖拽状态切换由 Python 端通过鼠标事件控制
    // JS 侧不需要额外操作
}

function reloadHandler(params) {
    location.reload();
}

// 页面加载完成后初始化桥接
document.addEventListener('DOMContentLoaded', function () {
    initBridge();
});
