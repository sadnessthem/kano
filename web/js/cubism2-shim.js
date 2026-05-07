/**
 * cubism2-shim.js — Cubism 2 Runtime 兼容填充
 *
 * pixi-live2d-display 加载时会计入 Cubism 2 代码路径（ZipLoader），
 * 即使我们只用 Cubism 4。提供 Cubism 2 的类存根以避免运行时错误。
 */
(function () {
    if (typeof window.Live2D === 'undefined') {
        var Live2D = {
            version: '2.1.00',
            logger: { log: function () {} },

            // Cubism 2 常量
            SRC_TO_X: 0,
            SRC_TO_Y: 1,
            SRC_TO_G_ANGLE: 2,
            SRC_TO_G_ANGLE_V: 3,
            SRC_TO_G_TIME: 4,
            SRC_TO_G_DECAY: 5,
            SRC_TO_G_DECAY_Z: 6,
            SRC_TO_GRAVITY: 7,
            SRC_TO_WIND: 8,
            SRC_TO_GRAVITY_X: 9,
            SRC_TO_GRAVITY_Y: 10,
            SRC_TO_GRAVITY_Z: 11,
            SRC_TO_WIND_X: 12,
            SRC_TO_WIND_Y: 13,
            SRC_TO_WIND_Z: 14,
            SRC_TO_LAST: 15,

            TARGET_X: 0,
            TARGET_Y: 1,
            TARGET_Z: 2,
            TARGET_ANGLE: 3,
            TARGET_G_ANGLE: 4,
            TARGET_G_ANGLE_V: 5,
            TARGET_G_TIME: 6,
            TARGET_G_DECAY: 7,
            TARGET_G_DECAY_Z: 8,
            TARGET_LAST: 9,

            // 物理预设
            PARAMETER_TYPE_X: 0,
            PARAMETER_TYPE_Y: 1,
            PARAMETER_TYPE_ANGLE: 2,
        };
        window.Live2D = Live2D;

        // AMotion — Cubism 2 动作基类
        function AMotion() {}
        AMotion.prototype = {
            updateParam: function () {},
            setFadeIn: function () {},
            setFadeOut: function () {},
            isFinished: function () { return true; },
            getDurationMS: function () { return 1000; },
            getLoopDurationMS: function () { return 1000; },
            setLoop: function () {},
            setLoopFadeIn: function () {},
            getFadeIn: function () { return 0; },
            getFadeOut: function () { return 0; },
        };
        window.AMotion = AMotion;

        // Live2DMotion — 继承 AMotion
        function Live2DMotion() { AMotion.call(this); }
        Live2DMotion.prototype = Object.create(AMotion.prototype);
        Live2DMotion.prototype.constructor = Live2DMotion;
        window.Live2DMotion = Live2DMotion;

        // MotionQueueManager
        function MotionQueueManager() { this._motions = []; }
        MotionQueueManager.prototype = {
            startMotion: function () {},
            updateParam: function () {},
            isFinished: function () { return true; },
            stopAllMotions: function () {},
        };
        window.MotionQueueManager = MotionQueueManager;

        // Model — 模拟 Live2D Model
        function Model() {
            this._paramValues = [];
            this._partOpacities = [];
        }
        Model.prototype = {
            getParamFloat: function () { return 0; },
            setParamFloat: function () {},
            addToParamFloat: function () {},
            getPartsOpacity: function () { return 1; },
            setPartsOpacity: function () {},
            update: function () {},
            draw: function () {},
            getCanvasWidth: function () { return 400; },
            getCanvasHeight: function () { return 600; },
            getParamIndex: function () { return 0; },
            getPartIndex: function () { return 0; },
            getPartDataCount: function () { return 1; },
        };
        window.Model = Model;

        // PhysicsManager — 物理模拟存根
        function PhysicsManager() {}
        PhysicsManager.prototype = { updateParam: function () {} };
        window.PhysicsManager = PhysicsManager;

        // PartData
        function PartData() {}
        PartData.prototype = {
            getPart: function () { return null; },
            getParameter: function () { return null; },
        };
        window.PartData = PartData;

        // PhysicsHair — Cubism 2 物理模拟
        function PhysicsHair() {}
        PhysicsHair.prototype = {
            updateParam: function () {},
            addParameter: function () {},
            addNormalization: function () {},
            setGravitationalAcceleration: function () {},
            setDragForce: function () {},
            setWind: function () {},
            setFrictionForce: function () {},
            setMass: function () {},
        };
        // 物理常量子对象
        PhysicsHair.Src = {
            SRC_TO_X: 0, SRC_TO_Y: 1, SRC_TO_G_ANGLE: 2,
            SRC_TO_G_ANGLE_V: 3, SRC_TO_G_TIME: 4,
            SRC_TO_G_DECAY: 5, SRC_TO_G_DECAY_Z: 6,
            SRC_TO_GRAVITY: 7, SRC_TO_WIND: 8,
        };
        PhysicsHair.Target = {
            TARGET_X: 0, TARGET_Y: 1, TARGET_Z: 2,
            TARGET_ANGLE: 3, TARGET_G_ANGLE: 4,
            TARGET_G_ANGLE_V: 5, TARGET_G_TIME: 6,
            TARGET_G_DECAY: 7, TARGET_G_DECAY_Z: 8,
        };
        window.PhysicsHair = PhysicsHair;

        // BaseData
        function BaseData() {}
        BaseData.prototype = {};
        window.BaseData = BaseData;

        console.log('[Shim] Cubism 2 shim loaded for Cubism 4 only environment');
    }

    // === PIXI.utils.EventEmitter polyfill ===
    // pixi-live2d-display expects PIXI.utils.EventEmitter, but PixiJS 6.5.10
    // browser bundle doesn't export it. Provide an eventemitter3-compatible shim.
    if (typeof PIXI !== 'undefined' && PIXI.utils && typeof PIXI.utils.EventEmitter === 'undefined') {
        function EventEmitter() {
            this._events = {};
        }
        EventEmitter.prototype = {
            on: function (evt, fn) {
                if (!this._events[evt]) this._events[evt] = [];
                this._events[evt].push(fn);
                return this;
            },
            once: function (evt, fn) {
                var self = this;
                function wrapper() {
                    fn.apply(self, arguments);
                    self.removeListener(evt, wrapper);
                }
                wrapper._orig = fn;
                return this.on(evt, wrapper);
            },
            emit: function (evt) {
                var fns = this._events[evt];
                if (!fns) return false;
                var args = Array.prototype.slice.call(arguments, 1);
                for (var i = 0; i < fns.length; i++) {
                    fns[i].apply(this, args);
                }
                return true;
            },
            removeListener: function (evt, fn) {
                var fns = this._events[evt];
                if (!fns) return this;
                if (!fn) {
                    delete this._events[evt];
                    return this;
                }
                for (var i = fns.length - 1; i >= 0; i--) {
                    if (fns[i] === fn || fns[i]._orig === fn) {
                        fns.splice(i, 1);
                    }
                }
                return this;
            },
            removeAllListeners: function (evt) {
                if (evt) {
                    delete this._events[evt];
                } else {
                    this._events = {};
                }
                return this;
            },
            listeners: function (evt) {
                return this._events[evt] || [];
            },
        };
        PIXI.utils.EventEmitter = EventEmitter;
        console.log('[Shim] Added PIXI.utils.EventEmitter polyfill');
    }
})();
