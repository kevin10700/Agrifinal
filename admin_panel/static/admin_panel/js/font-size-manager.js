/* ============================================
   AGRIVALE - Gestor de Tamaño de Fuente
   ============================================ */

const FontSizeManager = {
    currentSize: 'medium',
    
    init() {
        // Cargar tamaño guardado
        const savedSize = localStorage.getItem('admin_panel_font_size') || 'medium';
        this.setFontSize(savedSize);
        
        // Crear selector en el header si no existe
        this.createFontSizeSelector();
    },
    
    setFontSize(size) {
        this.currentSize = size;
        document.documentElement.setAttribute('data-font-size', size);
        localStorage.setItem('admin_panel_font_size', size);
        
        // Actualizar selector si existe
        const selector = document.getElementById('fontSizeSelector');
        if (selector) {
            selector.value = size;
        }
    },
    
    createFontSizeSelector() {
        const headerRight = document.querySelector('.header-right');
        if (!headerRight) return;
        
        // Crear contenedor del selector
        const selectorContainer = document.createElement('div');
        selectorContainer.className = 'font-size-selector';
        selectorContainer.style.cssText = `
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: var(--bg-hover);
            border-radius: var(--border-radius-sm);
        `;
        
        selectorContainer.innerHTML = `
            <i class="fas fa-text-height" style="color: var(--text-secondary); font-size: 0.9rem;"></i>
            <select id="fontSizeSelector" style="
                background: var(--bg-card);
                color: var(--text-primary);
                border: 1px solid var(--border-color);
                border-radius: var(--border-radius-sm);
                padding: 4px 8px;
                font-size: 0.85rem;
                cursor: pointer;
                outline: none;
            ">
                <option value="small">Pequeña</option>
                <option value="medium">Mediana</option>
                <option value="large">Grande</option>
                <option value="xlarge">Muy Grande</option>
            </select>
        `;
        
        // Agregar evento al selector
        const select = selectorContainer.querySelector('#fontSizeSelector');
        select.value = this.currentSize;
        select.addEventListener('change', (e) => {
            this.setFontSize(e.target.value);
        });
        
        // Insertar antes del botón de tema
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            headerRight.insertBefore(selectorContainer, themeToggle);
        } else {
            headerRight.appendChild(selectorContainer);
        }
    }
};

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    FontSizeManager.init();
});