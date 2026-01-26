/**
 * GB Game Studio - Emulator Integration
 * Simplified wrapper around binjgb WASM emulator.
 * 
 * Based on binjgb by Ben Smith (https://github.com/binji/binjgb)
 * MIT License
 */
"use strict";

// Constants
const SCREEN_WIDTH = 160;
const SCREEN_HEIGHT = 144;
const CPU_TICKS_PER_SECOND = 4194304;
const EVENT_NEW_FRAME = 1;
const EVENT_AUDIO_BUFFER_FULL = 2;
const EVENT_UNTIL_TICKS = 4;
const AUDIO_FRAMES = 4096;
const MAX_UPDATE_SEC = 5 / 60;

// Global state
let gbEmulator = null;
let binjgbModule = null;
let binjgbReady = false;

// Helper function to create WASM buffer
function makeWasmBuffer(module, ptr, size) {
    return new Uint8Array(module.HEAP8.buffer, ptr, size);
}

/**
 * Audio handler for the emulator
 */
class EmulatorAudio {
    constructor(module, e) {
        this.module = module;
        this.e = e;
        this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        this.gainNode = this.audioCtx.createGain();
        this.gainNode.gain.value = 0.5;
        this.gainNode.connect(this.audioCtx.destination);
        this.startSec = 0;
    }

    get sampleRate() {
        return this.audioCtx.sampleRate;
    }

    pushBuffer() {
        const nowSec = this.audioCtx.currentTime;
        const nowPlusLatency = nowSec + 0.1;
        
        if (this.gainNode.gain.value === 0) return;

        try {
            const srcLeft = makeWasmBuffer(
                this.module, this.module._get_audio_buffer_ptr(this.e, 0),
                AUDIO_FRAMES * 4);
            const srcRight = makeWasmBuffer(
                this.module, this.module._get_audio_buffer_ptr(this.e, 1),
                AUDIO_FRAMES * 4);
            
            const buffer = this.audioCtx.createBuffer(2, AUDIO_FRAMES, this.sampleRate);
            const leftData = buffer.getChannelData(0);
            const rightData = buffer.getChannelData(1);
            
            const srcLeftF32 = new Float32Array(srcLeft.buffer, srcLeft.byteOffset, AUDIO_FRAMES);
            const srcRightF32 = new Float32Array(srcRight.buffer, srcRight.byteOffset, AUDIO_FRAMES);
            leftData.set(srcLeftF32);
            rightData.set(srcRightF32);

            const bufferSource = this.audioCtx.createBufferSource();
            bufferSource.buffer = buffer;
            bufferSource.connect(this.gainNode);
            const startSec = Math.max(this.startSec, nowPlusLatency);
            bufferSource.start(startSec);
            this.startSec = startSec + buffer.duration;
        } catch (e) {
            console.warn('Audio push error:', e);
        }
    }

    pause() {
        this.audioCtx.suspend();
    }

    resume() {
        this.audioCtx.resume();
    }

    setVolume(value) {
        this.gainNode.gain.value = value;
    }

    destroy() {
        this.audioCtx.close();
    }
}

/**
 * Video handler for the emulator
 */
class EmulatorVideo {
    constructor(module, e, canvas) {
        this.module = module;
        this.e = e;
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.imageData = this.ctx.createImageData(SCREEN_WIDTH, SCREEN_HEIGHT);
        
        canvas.width = SCREEN_WIDTH;
        canvas.height = SCREEN_HEIGHT;
    }

    renderTexture() {
        const bufferPtr = this.module._get_frame_buffer_ptr(this.e);
        const buffer = makeWasmBuffer(this.module, bufferPtr, SCREEN_WIDTH * SCREEN_HEIGHT * 4);
        this.imageData.data.set(buffer);
        this.ctx.putImageData(this.imageData, 0, 0);
    }
}

/**
 * Main Emulator class (simplified - no rewind)
 */
class GBEmulator {
    constructor(module, romBuffer, canvas) {
        this.module = module;
        this.canvas = canvas;
        
        // Align ROM size up to 32k
        const size = (romBuffer.byteLength + 0x7fff) & ~0x7fff;
        this.romDataPtr = this.module._malloc(size);
        makeWasmBuffer(this.module, this.romDataPtr, size)
            .fill(0)
            .set(new Uint8Array(romBuffer));
        
        // Create audio first to get sample rate
        this.audio = new EmulatorAudio(module, null);
        
        // Create emulator instance
        this.e = this.module._emulator_new_simple(
            this.romDataPtr, size, this.audio.sampleRate, AUDIO_FRAMES, 2);
        
        if (this.e === 0) {
            throw new Error('Invalid ROM - emulator failed to initialize');
        }
        
        // Set up joypad callback - REQUIRED for input to work!
        this.joypadBufferPtr = this.module._joypad_new();
        this.module._emulator_set_default_joypad_callback(this.e, this.joypadBufferPtr);
        
        // Set audio emulator reference
        this.audio.e = this.e;
        
        // Create video handler
        this.video = new EmulatorVideo(module, this.e, canvas);
        
        // Animation state
        this.lastRafSec = 0;
        this.leftoverTicks = 0;
        this.rafCancelToken = null;
        this.fastForward = false;
        this.paused = false;
        
        // Key handlers
        this.boundKeyDown = this.onKeyDown.bind(this);
        this.boundKeyUp = this.onKeyUp.bind(this);
        
        // Set default palette (classic green)
        this.module._emulator_set_builtin_palette(this.e, 79);
    }

    get ticks() {
        return this.module._emulator_get_ticks_f64(this.e);
    }

    get isPaused() {
        return this.rafCancelToken === null;
    }

    run() {
        this.bindKeys();
        this.audio.resume();
        this.requestAnimationFrame();
    }

    stop() {
        this.unbindKeys();
        this.cancelAnimationFrame();
        this.audio.pause();
    }

    destroy() {
        this.stop();
        this.audio.destroy();
        this.module._joypad_delete(this.joypadBufferPtr);
        this.module._emulator_delete(this.e);
        this.module._free(this.romDataPtr);
    }

    bindKeys() {
        window.addEventListener('keydown', this.boundKeyDown);
        window.addEventListener('keyup', this.boundKeyUp);
    }

    unbindKeys() {
        window.removeEventListener('keydown', this.boundKeyDown);
        window.removeEventListener('keyup', this.boundKeyUp);
    }

    onKeyDown(event) {
        // Don't capture keys when user is typing in an input field
        if (this.isTypingInInput(event)) return;
        
        if (this.handleKey(event, true)) {
            event.preventDefault();
        }
    }

    onKeyUp(event) {
        // Don't capture keys when user is typing in an input field
        if (this.isTypingInInput(event)) return;
        
        if (this.handleKey(event, false)) {
            event.preventDefault();
        }
    }

    isTypingInInput(event) {
        const target = event.target;
        const tagName = target.tagName.toLowerCase();
        return tagName === 'input' || tagName === 'textarea' || target.isContentEditable;
    }

    handleKey(event, isDown) {
        // Map keyboard to joypad
        const keyMap = {
            'ArrowUp': 'setJoypUp',
            'ArrowDown': 'setJoypDown',
            'ArrowLeft': 'setJoypLeft',
            'ArrowRight': 'setJoypRight',
            // WASD alternatives
            'KeyW': 'setJoypUp',
            'KeyS': 'setJoypDown',
            'KeyA': 'setJoypLeft',
            'KeyD': 'setJoypRight',
            'KeyZ': 'setJoypB',
            'KeyX': 'setJoypA',
            'Enter': 'setJoypStart',
            'Tab': 'setJoypSelect',
        };

        const methodName = keyMap[event.code];
        if (methodName && this[methodName]) {
            this[methodName](isDown);
            return true;
        }
        
        // Special keys
        if (event.code === 'ShiftLeft') {
            this.fastForward = isDown;
            return true;
        }
        
        if (event.code === 'Space' && isDown) {
            this.togglePause();
            return true;
        }

        return false;
    }
    
    // Joypad methods - binjgb API (pass boolean directly like simple.js)
    setJoypDown(set) { this.module._set_joyp_down(this.e, set); }
    setJoypUp(set) { this.module._set_joyp_up(this.e, set); }
    setJoypLeft(set) { this.module._set_joyp_left(this.e, set); }
    setJoypRight(set) { this.module._set_joyp_right(this.e, set); }
    setJoypSelect(set) { this.module._set_joyp_select(this.e, set); }
    setJoypStart(set) { this.module._set_joyp_start(this.e, set); }
    setJoypB(set) { this.module._set_joyp_B(this.e, set); }
    setJoypA(set) { this.module._set_joyp_A(this.e, set); }

    togglePause() {
        if (this.isPaused) {
            this.resume();
        } else {
            this.pause();
        }
    }

    pause() {
        if (!this.isPaused) {
            this.cancelAnimationFrame();
            this.audio.pause();
            this.paused = true;
        }
    }

    resume() {
        if (this.isPaused) {
            this.lastRafSec = 0;
            this.leftoverTicks = 0;
            this.audio.startSec = 0;
            this.audio.resume();
            this.requestAnimationFrame();
            this.paused = false;
        }
    }

    requestAnimationFrame() {
        this.rafCancelToken = requestAnimationFrame(this.rafCallback.bind(this));
    }

    cancelAnimationFrame() {
        if (this.rafCancelToken !== null) {
            cancelAnimationFrame(this.rafCancelToken);
            this.rafCancelToken = null;
        }
    }

    rafCallback(rafSec) {
        this.requestAnimationFrame();
        
        rafSec = rafSec / 1000;
        let deltaSec = rafSec - this.lastRafSec;
        
        if (this.lastRafSec === 0 || deltaSec > MAX_UPDATE_SEC) {
            deltaSec = MAX_UPDATE_SEC;
        }
        this.lastRafSec = rafSec;

        const deltaTicks = deltaSec * CPU_TICKS_PER_SECOND * (this.fastForward ? 2 : 1);
        const runUntilTicks = this.ticks + deltaTicks + this.leftoverTicks;
        
        while (true) {
            const event = this.module._emulator_run_until_f64(this.e, runUntilTicks);
            if (event & EVENT_NEW_FRAME) {
                this.video.renderTexture();
            }
            if (event & EVENT_AUDIO_BUFFER_FULL) {
                this.audio.pushBuffer();
            }
            if (event & EVENT_UNTIL_TICKS) {
                break;
            }
        }
        
        this.leftoverTicks = runUntilTicks - this.ticks;
    }

    setVolume(value) {
        this.audio.setVolume(value);
    }
}

/**
 * Initialize the WASM module
 */
async function initBinjgb() {
    if (binjgbReady) return binjgbModule;
    
    // Load the WASM module
    binjgbModule = await Binjgb();
    binjgbReady = true;
    console.log('binjgb WASM module loaded');
    return binjgbModule;
}

/**
 * Load and start a ROM
 */
async function loadRom(romUrl, canvas) {
    // Stop existing emulator
    if (gbEmulator) {
        gbEmulator.destroy();
        gbEmulator = null;
    }
    
    // Initialize WASM module if needed
    const module = await initBinjgb();
    
    // Fetch ROM with cache busting
    const cacheBuster = `?t=${Date.now()}`;
    const response = await fetch(romUrl + cacheBuster, { cache: 'no-store' });
    if (!response.ok) {
        throw new Error(`Failed to load ROM: ${response.status}`);
    }
    
    const romBuffer = await response.arrayBuffer();
    console.log(`ROM loaded: ${romBuffer.byteLength} bytes`);
    
    // Create and start emulator
    gbEmulator = new GBEmulator(module, romBuffer, canvas);
    gbEmulator.run();
    
    return gbEmulator;
}

/**
 * Stop the current emulator
 */
function stopEmulator() {
    if (gbEmulator) {
        gbEmulator.destroy();
        gbEmulator = null;
    }
}

/**
 * Get current emulator instance
 */
function getEmulator() {
    return gbEmulator;
}

// Export functions for use in workspace
window.GBEmulator = {
    init: initBinjgb,
    loadRom: loadRom,
    stop: stopEmulator,
    get: getEmulator,
};
