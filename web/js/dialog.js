/**
 * dialog.js — 对话气泡系统
 *
 * 接收 Python 指令，显示对话气泡（打字机效果）
 */

const dialog = {
    _bubble: null,
    _textEl: null,
    _timer: null,
    _typingTimer: null,
    _isVisible: false,

    init() {
        this._bubble = document.getElementById('dialog-bubble');
        this._textEl = document.getElementById('dialog-text');
    },

    /**
     * 显示对话气泡
     * @param {Object} params - { text: '你好', duration: 3000 }
     */
    show(params) {
        if (!this._bubble || !this._textEl) {
            this.init();
        }
        if (!this._bubble) return;  // safety check

        const text = params.text || '';
        const duration = params.duration || 3000;

        // 清除之前的定时器和打字效果
        this._clearTimers();

        // 重置文本
        this._textEl.textContent = '';
        this._bubble.classList.remove('hidden');
        this._bubble.classList.add('visible');
        this._isVisible = true;

        // 打字机效果
        let charIndex = 0;
        const typingSpeed = 50;  // ms/字
        this._typingTimer = setInterval(() => {
            if (charIndex < text.length) {
                this._textEl.textContent += text[charIndex];
                charIndex++;
            } else {
                clearInterval(this._typingTimer);
                this._typingTimer = null;
            }
        }, typingSpeed);

        // 自动隐藏
        const totalDisplayTime = Math.max(duration, text.length * typingSpeed + 1500);
        this._timer = setTimeout(() => {
            this.hide();
        }, totalDisplayTime);
    },

    /**
     * 隐藏对话气泡
     */
    hide() {
        if (!this._bubble) return;
        this._clearTimers();
        this._bubble.classList.remove('visible');
        this._bubble.classList.add('hidden');
        this._isVisible = false;
    },

    _clearTimers() {
        if (this._timer) {
            clearTimeout(this._timer);
            this._timer = null;
        }
        if (this._typingTimer) {
            clearInterval(this._typingTimer);
            this._typingTimer = null;
        }
    }
};

// DOM 加载后初始化
document.addEventListener('DOMContentLoaded', function () {
    dialog.init();
});
