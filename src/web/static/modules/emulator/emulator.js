/**
 * GB Game Studio - Emulator Module
 * 
 * In-browser Game Boy emulator controls and functions.
 */

window.emulatorLoaded = false;

async function updateEmulatorState() {
    const { currentProject } = window.gbStudio;
    
    // Check if project has been compiled (status is 'compiled' or 'verified')
    const hasRom = currentProject && ['compiled', 'verified'].includes(currentProject.status);
    const overlay = document.getElementById('emulator-overlay');
    const playBtn = document.getElementById('emu-play-btn');
    const pauseBtn = document.getElementById('emu-pause-btn');
    const reloadBtn = document.getElementById('emu-reload-btn');
    
    if (!overlay) return; // Guard against missing elements
    
    if (hasRom) {
        playBtn.disabled = false;
        reloadBtn.disabled = false;
        
        // Update overlay message
        const message = overlay.querySelector('.emulator-message');
        if (!window.emulatorLoaded) {
            message.innerHTML = `
                <span class="emulator-icon">🎮</span>
                <p>Click Play to start the game</p>
            `;
        }
    } else {
        playBtn.disabled = true;
        pauseBtn.disabled = true;
        reloadBtn.disabled = true;
        overlay.classList.remove('hidden');
        
        const message = overlay.querySelector('.emulator-message');
        message.innerHTML = `
            <span class="emulator-icon">🔨</span>
            <p>Build the project first</p>
        `;
    }
}

async function handleEmulatorPlay() {
    const { currentProjectId } = window.gbStudio;
    if (!currentProjectId) return;
    
    const overlay = document.getElementById('emulator-overlay');
    const canvas = document.getElementById('emulator-canvas');
    const playBtn = document.getElementById('emu-play-btn');
    const pauseBtn = document.getElementById('emu-pause-btn');
    
    try {
        // Show loading state
        const message = overlay.querySelector('.emulator-message');
        message.innerHTML = `
            <span class="emulator-icon">⏳</span>
            <p>Loading ROM...</p>
        `;
        
        // Get ROM URL
        const romUrl = `/api/v2/projects/${currentProjectId}/files/rom`;
        
        // Load ROM into emulator
        await window.GBEmulator.loadRom(romUrl, canvas);
        
        // Hide overlay
        overlay.classList.add('hidden');
        window.emulatorLoaded = true;
        
        // Update button states
        playBtn.disabled = true;
        pauseBtn.disabled = false;
        
    } catch (error) {
        console.error('Emulator error:', error);
        const message = overlay.querySelector('.emulator-message');
        message.innerHTML = `
            <span class="emulator-icon">❌</span>
            <p>Failed to load ROM: ${error.message}</p>
        `;
    }
}

function handleEmulatorPause() {
    const emu = window.GBEmulator.get();
    if (!emu) return;
    
    const playBtn = document.getElementById('emu-play-btn');
    const pauseBtn = document.getElementById('emu-pause-btn');
    
    if (emu.isPaused) {
        emu.resume();
        pauseBtn.textContent = '⏸️ Pause';
    } else {
        emu.pause();
        pauseBtn.textContent = '▶️ Resume';
    }
}

async function handleEmulatorReload() {
    // Stop current emulator
    window.GBEmulator.stop();
    window.emulatorLoaded = false;
    
    const overlay = document.getElementById('emulator-overlay');
    overlay.classList.remove('hidden');
    
    const playBtn = document.getElementById('emu-play-btn');
    const pauseBtn = document.getElementById('emu-pause-btn');
    playBtn.disabled = false;
    pauseBtn.disabled = true;
    pauseBtn.textContent = '⏸️ Pause';
    
    // Auto-play after reload
    await handleEmulatorPlay();
}

function handleEmulatorVolume(e) {
    const emu = window.GBEmulator.get();
    if (emu) {
        emu.setVolume(e.target.value / 100);
    }
}

// Export functions
window.updateEmulatorState = updateEmulatorState;
window.handleEmulatorPlay = handleEmulatorPlay;
window.handleEmulatorPause = handleEmulatorPause;
window.handleEmulatorReload = handleEmulatorReload;
window.handleEmulatorVolume = handleEmulatorVolume;
