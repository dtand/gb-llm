/**
 * GB Game Studio - Sprites Module
 * 
 * Sprite viewer and editor for Game Boy 2bpp graphics.
 */

// Game Boy 4-color palette (classic green shades)
const GB_PALETTE = [
    '#9bbc0f', // Lightest (color 0)
    '#8bac0f', // Light (color 1)
    '#306230', // Dark (color 2)
    '#0f380f'  // Darkest (color 3)
];

// Alternative DMG palette (more authentic)
const DMG_PALETTE = [
    '#e0f8d0', // Lightest
    '#88c070', // Light
    '#346856', // Dark
    '#081820'  // Darkest
];

let spriteData = null;

// === Sprite Editor State ===

const spriteEditor = {
    canvas: null,
    ctx: null,
    previewCanvas: null,
    previewCtx: null,
    width: 8,
    height: 8,
    pixels: null,  // 2D array of color indices (0-3)
    currentColor: 0,
    currentTool: 'pencil',
    isDrawing: false,
    editingSprite: null,  // Name of sprite being edited, null for new
    scale: 24,  // Pixels per GB pixel in editor
};

// === Sprite Loading ===

async function loadSprites() {
    const { currentProjectId } = window.gbStudio;
    if (!currentProjectId) return;
    
    const emptyEl = document.getElementById('sprites-empty');
    const gridEl = document.getElementById('sprites-grid');
    
    try {
        spriteData = await apiRequest(`/api/v2/projects/${currentProjectId}/sprites`);
        renderSprites();
    } catch (error) {
        console.error('Failed to load sprites:', error);
        emptyEl.style.display = 'flex';
        gridEl.innerHTML = '';
    }
}

function renderSprites() {
    const emptyEl = document.getElementById('sprites-empty');
    const gridEl = document.getElementById('sprites-grid');
    
    if (!spriteData || spriteData.sprites.length === 0) {
        emptyEl.style.display = 'flex';
        gridEl.innerHTML = '';
        return;
    }
    
    emptyEl.style.display = 'none';
    
    gridEl.innerHTML = spriteData.sprites.map((sprite, idx) => `
        <div class="sprite-card" data-index="${idx}">
            <canvas class="sprite-canvas" 
                    id="sprite-canvas-${idx}" 
                    width="${sprite.width}" 
                    height="${sprite.height}"
                    title="${sprite.name}">
            </canvas>
            <div class="sprite-info">
                <span class="sprite-name">${formatSpriteName(sprite.name)}</span>
                <span class="sprite-size">${sprite.width}×${sprite.height}</span>
            </div>
            <button class="sprite-edit-btn" onclick="editSprite(${idx})" title="Edit sprite">
                ✏️ Edit
            </button>
        </div>
    `).join('');
    
    // Render each sprite to its canvas
    spriteData.sprites.forEach((sprite, idx) => {
        const canvas = document.getElementById(`sprite-canvas-${idx}`);
        if (canvas) {
            renderSpriteToCanvas(canvas, sprite);
        }
    });
}

function formatSpriteName(name) {
    // Convert snake_case to Title Case
    return name
        .replace(/_tile$|_tiles$|_sprite$|_data$/, '') // Remove common suffixes
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * Render Game Boy 2bpp tile data to a canvas.
 * 
 * GB tiles use 2 bits per pixel, stored as 2 bytes per row.
 * Byte 0 = low bit of each pixel, Byte 1 = high bit.
 * Color = (highBit << 1) | lowBit
 */
function renderSpriteToCanvas(canvas, sprite) {
    const ctx = canvas.getContext('2d');
    const { width, height, data } = sprite;
    const palette = DMG_PALETTE;
    
    // Scale factor for display (make small sprites visible)
    const scale = width <= 8 ? 6 : (width <= 16 ? 4 : 2);
    canvas.style.width = `${width * scale}px`;
    canvas.style.height = `${height * scale}px`;
    canvas.style.imageRendering = 'pixelated';
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    // Process tile data (2 bytes per row, 8 pixels per row)
    let byteIndex = 0;
    
    for (let tileY = 0; tileY < height; tileY += 8) {
        for (let tileX = 0; tileX < width; tileX += 8) {
            // Each 8x8 tile is 16 bytes
            for (let row = 0; row < 8 && (tileY + row) < height; row++) {
                if (byteIndex + 1 >= data.length) break;
                
                const lowByte = data[byteIndex];
                const highByte = data[byteIndex + 1];
                byteIndex += 2;
                
                // Decode 8 pixels from this row
                for (let bit = 7; bit >= 0 && (tileX + (7 - bit)) < width; bit--) {
                    const lowBit = (lowByte >> bit) & 1;
                    const highBit = (highByte >> bit) & 1;
                    const colorIndex = (highBit << 1) | lowBit;
                    
                    const x = tileX + (7 - bit);
                    const y = tileY + row;
                    
                    ctx.fillStyle = palette[colorIndex];
                    ctx.fillRect(x, y, 1, 1);
                }
            }
        }
    }
}

// === Sprite Editor ===

function initSpriteEditor() {
    spriteEditor.canvas = document.getElementById('sprite-editor-canvas');
    spriteEditor.ctx = spriteEditor.canvas.getContext('2d');
    spriteEditor.previewCanvas = document.getElementById('sprite-preview-canvas');
    spriteEditor.previewCtx = spriteEditor.previewCanvas.getContext('2d');
    
    // Mouse events for drawing
    spriteEditor.canvas.addEventListener('mousedown', handleEditorMouseDown);
    spriteEditor.canvas.addEventListener('mousemove', handleEditorMouseMove);
    spriteEditor.canvas.addEventListener('mouseup', handleEditorMouseUp);
    spriteEditor.canvas.addEventListener('mouseleave', handleEditorMouseUp);
    
    // Touch support
    spriteEditor.canvas.addEventListener('touchstart', handleEditorTouchStart);
    spriteEditor.canvas.addEventListener('touchmove', handleEditorTouchMove);
    spriteEditor.canvas.addEventListener('touchend', handleEditorMouseUp);
    
    // Tool buttons
    document.querySelectorAll('.tool-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            spriteEditor.currentTool = btn.dataset.tool;
        });
    });
    
    // Palette buttons
    document.querySelectorAll('.palette-color').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.palette-color').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            spriteEditor.currentColor = parseInt(btn.dataset.color);
        });
    });
    
    // Size buttons
    document.querySelectorAll('.size-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.size-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const [w, h] = btn.dataset.size.split('x').map(Number);
            resizeSpriteCanvas(w, h);
        });
    });
    
    // Create sprite button
    document.getElementById('create-sprite-btn').addEventListener('click', () => {
        showSpriteEditor(null);
    });
    
    // Save button
    document.getElementById('save-sprite-btn').addEventListener('click', saveSprite);
}

function showSpriteEditor(existingSprite = null) {
    const modal = document.getElementById('sprite-editor-modal');
    const title = document.getElementById('sprite-editor-title');
    const nameInput = document.getElementById('sprite-name-input');
    
    spriteEditor.editingSprite = existingSprite;
    
    if (existingSprite) {
        title.textContent = 'Edit Sprite';
        nameInput.value = existingSprite.name;
        resizeSpriteCanvas(existingSprite.width, existingSprite.height);
        loadSpriteIntoEditor(existingSprite);
        
        // Update size button
        const sizeStr = `${existingSprite.width}x${existingSprite.height}`;
        document.querySelectorAll('.size-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.size === sizeStr);
        });
    } else {
        title.textContent = 'Create Sprite';
        nameInput.value = '';
        resizeSpriteCanvas(8, 8);
        clearSpriteCanvas();
        
        // Reset to 8x8
        document.querySelectorAll('.size-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.size === '8x8');
        });
    }
    
    // Reset tools
    spriteEditor.currentColor = 0;
    spriteEditor.currentTool = 'pencil';
    document.querySelectorAll('.palette-color').forEach(b => b.classList.toggle('active', b.dataset.color === '0'));
    document.querySelectorAll('.tool-btn').forEach(b => b.classList.toggle('active', b.dataset.tool === 'pencil'));
    
    modal.style.display = 'flex';
}

function hideSpriteEditor() {
    document.getElementById('sprite-editor-modal').style.display = 'none';
}

function resizeSpriteCanvas(width, height) {
    spriteEditor.width = width;
    spriteEditor.height = height;
    
    // Update canvas size
    spriteEditor.canvas.width = width;
    spriteEditor.canvas.height = height;
    spriteEditor.previewCanvas.width = width;
    spriteEditor.previewCanvas.height = height;
    
    // Scale for display
    const scale = width <= 8 ? 24 : (width <= 16 ? 16 : 12);
    spriteEditor.scale = scale;
    spriteEditor.canvas.style.width = `${width * scale}px`;
    spriteEditor.canvas.style.height = `${height * scale}px`;
    spriteEditor.previewCanvas.style.width = `${width * 4}px`;
    spriteEditor.previewCanvas.style.height = `${height * 4}px`;
    
    // Initialize pixel array
    spriteEditor.pixels = Array(height).fill(null).map(() => Array(width).fill(0));
    
    // Update grid overlay
    updateGridOverlay();
    
    renderEditorCanvas();
    updatePreview();
}

function updateGridOverlay() {
    const overlay = document.getElementById('sprite-grid-overlay');
    const { width, height, scale } = spriteEditor;
    
    overlay.style.width = `${width * scale}px`;
    overlay.style.height = `${height * scale}px`;
    overlay.style.backgroundSize = `${scale}px ${scale}px`;
}

function loadSpriteIntoEditor(sprite) {
    const { width, height, data } = sprite;
    spriteEditor.pixels = Array(height).fill(null).map(() => Array(width).fill(0));
    
    // Decode 2bpp data into pixels array
    let byteIndex = 0;
    
    for (let tileY = 0; tileY < height; tileY += 8) {
        for (let tileX = 0; tileX < width; tileX += 8) {
            for (let row = 0; row < 8 && (tileY + row) < height; row++) {
                if (byteIndex + 1 >= data.length) break;
                
                const lowByte = data[byteIndex];
                const highByte = data[byteIndex + 1];
                byteIndex += 2;
                
                for (let bit = 7; bit >= 0 && (tileX + (7 - bit)) < width; bit--) {
                    const lowBit = (lowByte >> bit) & 1;
                    const highBit = (highByte >> bit) & 1;
                    const colorIndex = (highBit << 1) | lowBit;
                    
                    const x = tileX + (7 - bit);
                    const y = tileY + row;
                    spriteEditor.pixels[y][x] = colorIndex;
                }
            }
        }
    }
    
    renderEditorCanvas();
    updatePreview();
}

function renderEditorCanvas() {
    const { ctx, width, height, pixels } = spriteEditor;
    
    ctx.clearRect(0, 0, width, height);
    
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const colorIndex = pixels[y][x];
            ctx.fillStyle = DMG_PALETTE[colorIndex];
            ctx.fillRect(x, y, 1, 1);
        }
    }
}

function updatePreview() {
    const { previewCtx, width, height, pixels } = spriteEditor;
    
    previewCtx.clearRect(0, 0, width, height);
    
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const colorIndex = pixels[y][x];
            previewCtx.fillStyle = DMG_PALETTE[colorIndex];
            previewCtx.fillRect(x, y, 1, 1);
        }
    }
}

function getEditorPixelCoords(e) {
    const rect = spriteEditor.canvas.getBoundingClientRect();
    const scaleX = spriteEditor.width / rect.width;
    const scaleY = spriteEditor.height / rect.height;
    
    const x = Math.floor((e.clientX - rect.left) * scaleX);
    const y = Math.floor((e.clientY - rect.top) * scaleY);
    
    return { x: Math.max(0, Math.min(x, spriteEditor.width - 1)), 
             y: Math.max(0, Math.min(y, spriteEditor.height - 1)) };
}

function handleEditorMouseDown(e) {
    spriteEditor.isDrawing = true;
    applyTool(e);
}

function handleEditorMouseMove(e) {
    if (!spriteEditor.isDrawing) return;
    applyTool(e);
}

function handleEditorMouseUp() {
    spriteEditor.isDrawing = false;
}

function handleEditorTouchStart(e) {
    e.preventDefault();
    spriteEditor.isDrawing = true;
    const touch = e.touches[0];
    applyTool({ clientX: touch.clientX, clientY: touch.clientY });
}

function handleEditorTouchMove(e) {
    e.preventDefault();
    if (!spriteEditor.isDrawing) return;
    const touch = e.touches[0];
    applyTool({ clientX: touch.clientX, clientY: touch.clientY });
}

function applyTool(e) {
    const { x, y } = getEditorPixelCoords(e);
    const { currentTool, currentColor, pixels, width, height } = spriteEditor;
    
    switch (currentTool) {
        case 'pencil':
            pixels[y][x] = currentColor;
            break;
        case 'eraser':
            pixels[y][x] = 0;  // Lightest color
            break;
        case 'fill':
            floodFill(x, y, pixels[y][x], currentColor);
            break;
    }
    
    renderEditorCanvas();
    updatePreview();
}

function floodFill(startX, startY, targetColor, fillColor) {
    if (targetColor === fillColor) return;
    
    const { pixels, width, height } = spriteEditor;
    const stack = [[startX, startY]];
    
    while (stack.length > 0) {
        const [x, y] = stack.pop();
        
        if (x < 0 || x >= width || y < 0 || y >= height) continue;
        if (pixels[y][x] !== targetColor) continue;
        
        pixels[y][x] = fillColor;
        
        stack.push([x + 1, y]);
        stack.push([x - 1, y]);
        stack.push([x, y + 1]);
        stack.push([x, y - 1]);
    }
}

function clearSpriteCanvas() {
    const { width, height } = spriteEditor;
    spriteEditor.pixels = Array(height).fill(null).map(() => Array(width).fill(0));
    renderEditorCanvas();
    updatePreview();
}

function flipSpriteH() {
    const { pixels, width, height } = spriteEditor;
    for (let y = 0; y < height; y++) {
        pixels[y].reverse();
    }
    renderEditorCanvas();
    updatePreview();
}

function flipSpriteV() {
    spriteEditor.pixels.reverse();
    renderEditorCanvas();
    updatePreview();
}

function pixelsTo2bpp() {
    const { pixels, width, height } = spriteEditor;
    const bytes = [];
    
    // Process in 8x8 tile chunks
    for (let tileY = 0; tileY < height; tileY += 8) {
        for (let tileX = 0; tileX < width; tileX += 8) {
            // Each tile row is 2 bytes
            for (let row = 0; row < 8 && (tileY + row) < height; row++) {
                let lowByte = 0;
                let highByte = 0;
                
                for (let bit = 7; bit >= 0; bit--) {
                    const x = tileX + (7 - bit);
                    const y = tileY + row;
                    const colorIndex = x < width ? pixels[y][x] : 0;
                    
                    if (colorIndex & 1) lowByte |= (1 << bit);
                    if (colorIndex & 2) highByte |= (1 << bit);
                }
                
                bytes.push(lowByte, highByte);
            }
        }
    }
    
    return bytes;
}

async function saveSprite() {
    const nameInput = document.getElementById('sprite-name-input');
    let name = nameInput.value.trim();
    const { currentProjectId } = window.gbStudio;
    
    // Validate name
    if (!name) {
        alert('Please enter a sprite name');
        nameInput.focus();
        return;
    }
    
    // Ensure valid C identifier
    name = name.toLowerCase().replace(/[^a-z0-9_]/g, '_');
    if (!/^[a-z_]/.test(name)) {
        name = 'sprite_' + name;
    }
    
    // Add suffix if not present
    if (!name.endsWith('_tile') && !name.endsWith('_tiles') && !name.endsWith('_sprite')) {
        name += '_tile';
    }
    
    const data = pixelsTo2bpp();
    
    try {
        await apiRequest(`/api/v2/projects/${currentProjectId}/sprites`, {
            method: 'POST',
            body: JSON.stringify({
                name: name,
                width: spriteEditor.width,
                height: spriteEditor.height,
                data: data,
                replace: spriteEditor.editingSprite?.name || null
            })
        });
        
        hideSpriteEditor();
        loadSprites();  // Refresh sprite list
        addLogEntry('success', `Sprite "${name}" saved`);
    } catch (error) {
        console.error('Failed to save sprite:', error);
        addLogEntry('error', `Failed to save sprite: ${error.message}`);
    }
}

function editSprite(index) {
    if (!spriteData || !spriteData.sprites[index]) return;
    showSpriteEditor(spriteData.sprites[index]);
}

// Initialize editor when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Delay init until elements exist
    setTimeout(initSpriteEditor, 100);
});

// Export functions
window.loadSprites = loadSprites;
window.editSprite = editSprite;
window.clearSpriteCanvas = clearSpriteCanvas;
window.flipSpriteH = flipSpriteH;
window.flipSpriteV = flipSpriteV;
window.hideSpriteEditor = hideSpriteEditor;
