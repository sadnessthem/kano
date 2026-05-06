/**
 * live2d-loader.js — 加载并初始化 Live2D 模型
 *
 * 使用 PixiJS 6 + pixi-live2d-display
 * 模型路径相对于 index.html 的位置：../models/{model_name}/runtime/
 */

// Global config
var CONFIG = {
    modelName: 'hiyori',
    get modelPath() {
        return '../models/' + this.modelName + '/runtime/hiyori_pro_t11.model3.json';
    }
};

// PixiJS Application instance
var app = null;
var model = null;

/**
 * Initialize PixiJS + load Live2D model
 */
async function initLive2D() {
    try {
        console.log('[Live2D] Starting init...');
        console.log('[Live2D] PIXI:', typeof PIXI);
        console.log('[Live2D] PIXI.live2d:', typeof (PIXI || {}).live2d);
        console.log('[Live2D] Live2DCubismCore:', typeof Live2DCubismCore);

        // Check WebGL
        var tc = document.createElement('canvas');
        var webgl = !!(tc.getContext('webgl') || tc.getContext('webgl2'));
        console.log('[Live2D] WebGL:', webgl);
        if (!webgl) { console.error('[Live2D] No WebGL'); return; }

        // Create PixiJS Application
        console.log('[Live2D] Creating Application (' + window.innerWidth + 'x' + window.innerHeight + ')...');
        app = new PIXI.Application({
            width: window.innerWidth,
            height: window.innerHeight,
            backgroundAlpha: 0,          // 透明背景（PixiJS 6 正确方式）
            antialias: true,
            resolution: window.devicePixelRatio || 1,
            autoDensity: true,
        });
        console.log('[Live2D] Application ready');

        // Add canvas to DOM
        var container = document.getElementById('role-container');
        container.appendChild(app.view);
        // Force canvas and container backgrounds transparent via inline style
        app.view.style.background = 'transparent';
        app.view.style.backgroundColor = 'transparent';
        container.style.background = 'transparent';
        container.style.backgroundColor = 'transparent';

        // Model centering
        app.stage.x = window.innerWidth / 2;
        app.stage.y = window.innerHeight;

        // Load model
        console.log('[Live2D] Loading model:', CONFIG.modelPath);
        model = await PIXI.live2d.Live2DModel.from(CONFIG.modelPath);
        console.log('[Live2D] Model loaded: ' + model.width + 'x' + model.height);

        // Anchor bottom-center
        model.anchor.set(0.5, 1.0);
        model.position.set(0, 0);

        // Auto scale
        var scaleX = (window.innerHeight * 0.9) / model.height;
        var scaleY = (window.innerWidth * 0.9) / model.width;
        model.scale.set(Math.min(scaleX, scaleY));
        console.log('[Live2D] Scale: ' + Math.min(scaleX, scaleY));

        app.stage.addChild(model);

        // Cap frame rate to 30 FPS (性能优化)
        app.ticker.maxFPS = 30;

        // Enable auto eye blink
        if (model.internalModel && model.internalModel.motionManager) {
            model.internalModel.motionManager.eyeBlinkEnabled = true;
        }

        // Start idle animation loop
        startIdleLoop();

        // Force all page backgrounds transparent
        document.documentElement.style.backgroundColor = 'transparent';
        document.body.style.backgroundColor = 'transparent';

        // Save global references
        window.live2dApp = app;
        window.live2dModel = model;

        console.log('[Live2D] Init complete');

        // Notify behavior player
        if (window.player) {
            window.player.onModelReady();
        }

    } catch (error) {
        console.error('[Live2D] Error:', error.message || error);
        if (error.stack) console.error('[Live2D] Stack:', error.stack.substring(0, 300));
        window.__live2dError = error.message || String(error);
    }
}

/**
 * Idle animation loop
 */
function startIdleLoop() {
    if (!model) return;

    var idleMotions = ['Idle'];
    var currentIndex = 0;

    async function playNextIdle() {
        if (!model) return;
        try {
            var group = idleMotions[currentIndex % idleMotions.length];
            await model.motion(group, 0, PIXI.live2d.MotionPriority.IDLE);
        } catch (e) { /* interrupted, normal */ }
        currentIndex++;
    }

    model.on('motionFinish', function(e) {
        if (e && e.group === 'Idle') {
            setTimeout(playNextIdle, 1000);
        }
    });

    setTimeout(playNextIdle, 500);
}

// Resize handler
window.addEventListener('resize', function() {
    if (app) {
        app.renderer.resize(window.innerWidth, window.innerHeight);
        app.stage.x = window.innerWidth / 2;
        if (typeof _miniModeActive !== 'undefined' && _miniModeActive) {
            // 迷你模式：由 _applyMiniMode 处理缩放和位置
            if (typeof _applyMiniMode === 'function') _applyMiniMode();
        } else {
            app.stage.y = window.innerHeight;
        }
    }
});

// Start on DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    initLive2D();
});
