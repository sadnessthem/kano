/**
 * behavior_player.js — 角色动作/表情控制
 *
 * 接收 Python 指令，控制 Live2D 模型播放动作和切换表情
 */

const player = {
    _model: null,
    _ready: false,

    /**
     * 模型就绪回调（由 live2d-loader.js 调用）
     */
    onModelReady() {
        this._model = window.live2dModel;
        this._ready = true;
        console.log('[Player] Model ready');
    },

    /**
     * 播放动作
     * @param {Object} params - { group: 'Tap', index: 0, priority: 3 }
     */
    async playMotion(params) {
        if (!this._ready || !this._model) return;
        try {
            const group = params.group || 'Tap';
            const index = params.index || 0;
            const priority = params.priority !== undefined
                ? params.priority
                : PIXI.live2d.MotionPriority.NORMAL;

            console.log(`[Player] playMotion: ${group}[${index}], priority=${priority}`);
            await this._model.motion(group, index, priority);
        } catch (e) {
            console.warn('[Player] Motion failed:', e.message);
        }
    },

    /**
     * 切换表情
     * @param {Object} params - { expression_id: 'smile' }
     */
    async setExpression(params) {
        if (!this._ready || !this._model) return;
        try {
            const exprId = params.expression_id || params.expression_id;
            if (!exprId) return;
            await this._model.expression(exprId);
            console.log(`[Player] setExpression: ${exprId}`);
        } catch (e) {
            console.warn('[Player] Expression failed:', e.message);
        }
    },
};
