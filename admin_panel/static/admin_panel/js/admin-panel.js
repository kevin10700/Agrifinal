/* ============================================
   AGRIVALE - Panel Administrativo
   JavaScript Principal
   ============================================ */

// ===== CONFIGURACIÓN DE TEMA =====
const ThemeManager = {
    currentTheme: 'light',
    
    init() {
        // Cargar tema guardado
        const savedTheme = localStorage.getItem('admin_panel_theme') || 'light';
        this.setTheme(savedTheme);
        
        // Escuchar cambios en el botón
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                this.toggle();
            });
        }
    },
    
    setTheme(theme) {
        this.currentTheme = theme;
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('admin_panel_theme', theme);
        
        // Actualizar icono del botón
        const themeIcon = document.querySelector('#themeToggle i');
        if (themeIcon) {
            themeIcon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
    },
    
    toggle() {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme);
    }
};

// ===== CONFIGURACIÓN DE SIDEBAR =====
const SidebarManager = {
    isCollapsed: false,
    
    init() {
        // Cargar estado guardado
        const savedState = localStorage.getItem('admin_panel_sidebar_collapsed');
        if (savedState === 'true') {
            this.collapse();
        }
        
        // Escuchar cambios en el botón de toggle
        document.getElementById('sidebarToggle')?.addEventListener('click', () => {
            this.toggle();
        });
        
        // Menú móvil
        document.getElementById('mobileMenuToggle')?.addEventListener('click', () => {
            this.toggleMobile();
        });
        
        // Cerrar sidebar al hacer clic fuera en móvil
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768) {
                const sidebar = document.getElementById('sidebar');
                const toggle = document.getElementById('mobileMenuToggle');
                
                if (!sidebar.contains(e.target) && !toggle.contains(e.target) && sidebar.classList.contains('open')) {
                    this.closeMobile();
                }
            }
        });
    },
    
    collapse() {
        document.getElementById('sidebar')?.classList.add('collapsed');
        this.isCollapsed = true;
        localStorage.setItem('admin_panel_sidebar_collapsed', 'true');
    },
    
    expand() {
        document.getElementById('sidebar')?.classList.remove('collapsed');
        this.isCollapsed = false;
        localStorage.setItem('admin_panel_sidebar_collapsed', 'false');
    },
    
    toggle() {
        if (this.isCollapsed) {
            this.expand();
        } else {
            this.collapse();
        }
    },
    
    toggleMobile() {
        const sidebar = document.getElementById('sidebar');
        sidebar?.classList.toggle('open');
    },
    
    closeMobile() {
        const sidebar = document.getElementById('sidebar');
        sidebar?.classList.remove('open');
    }
};

// ===== BUSCADOR GLOBAL =====
const GlobalSearch = {
    init() {
        const searchInput = document.getElementById('globalSearch');
        if (!searchInput) return;
        
        let debounceTimer;
        
        searchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                this.search(e.target.value);
            }, 300);
        });
    },
    
    search(query) {
        if (query.length < 2) return;
        
        // Aquí implementarías la lógica de búsqueda
        console.log('Buscando:', query);
        // Por ahora solo mostramos un ejemplo
        // En el futuro esto podría hacer una petición AJAX
    }
};

// ===== NOTIFICACIONES TOAST =====
const Toast = {
    show(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        // Mapa de colores por tipo
        const colors = {
            success: '#27ae60',
            error: '#e74c3c',
            warning: '#f39c12',
            info: '#3498db'
        };
        const bgColor = colors[type] || colors.info;
        
        // Iconos por tipo
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        const iconName = icons[type] || icons.info;
        
        // Actualizar el HTML del toast
        toast.innerHTML = `
            <i class="fas fa-${iconName}"></i>
            <span>${message}</span>
        `;
        
        // Estilos del toast
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 16px 20px;
            background: ${bgColor};
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            display: flex;
            align-items: center;
            gap: 12px;
            z-index: 9999;
            animation: slideInRight 0.3s ease;
            max-width: 400px;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
};

// ===== CONFIRMACIONES MODALES =====
const ConfirmModal = {
    show(message, onConfirm, onCancel) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Confirmar Acción</h3>
                </div>
                <div class="modal-body">
                    <p>${message}</p>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" id="modalCancel">Cancelar</button>
                    <button class="btn btn-primary" id="modalConfirm">Confirmar</button>
                </div>
            </div>
        `;
        
        // Estilos del modal
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            animation: fadeIn 0.2s ease;
        `;
        
        const content = modal.querySelector('.modal-content');
        content.style.cssText = `
            background: var(--bg-card);
            border-radius: 12px;
            padding: 24px;
            max-width: 500px;
            width: 90%;
            box-shadow: 0 8px 24px rgba(0,0,0,0.2);
            animation: scaleIn 0.2s ease;
        `;
        
        document.body.appendChild(modal);
        
        modal.querySelector('#modalCancel').addEventListener('click', () => {
            modal.remove();
            if (onCancel) onCancel();
        });
        
        modal.querySelector('#modalConfirm').addEventListener('click', () => {
            modal.remove();
            if (onConfirm) onConfirm();
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
                if (onCancel) onCancel();
            }
        });
    }
};

// ===== DROPDOWN DE NOTIFICACIONES =====
const NotificationDropdown = {
    init() {
        const bellToggle = document.getElementById('bellToggle');
        const notificationMenu = document.getElementById('notificationMenu');
        if (!bellToggle || !notificationMenu) return;
        bellToggle.addEventListener('click', (e) => {
            e.preventDefault();
            notificationMenu.classList.toggle('show');
        });
        document.addEventListener('click', (e) => {
            if (!bellToggle.contains(e.target) && !notificationMenu.contains(e.target)) {
                notificationMenu.classList.remove('show');
            }
        });
    }
};

// ===== DROPDOWN DEL SIDEBAR =====
const SidebarDropdown = {
    init() {
        // Manejar clicks en los dropdown toggles del sidebar
        document.querySelectorAll('.dropdown-toggle[data-dropdown]').forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const dropdownId = toggle.dataset.dropdown;
                const menu = document.getElementById(dropdownId + 'DropdownMenu');
                if (!menu) return;
                
                // Cerrar otros dropdowns abiertos
                document.querySelectorAll('.dropdown-menu.show').forEach(m => {
                    if (m.id !== menu.id) {
                        m.classList.remove('show');
                    }
                });
                
                // Toggle del menú actual
                menu.classList.toggle('show');
                
                // Rotar el icono del chevron
                const icon = toggle.querySelector('.dropdown-icon');
                if (icon) {
                    icon.style.transform = menu.classList.contains('show') ? 'rotate(180deg)' : 'rotate(0deg)';
                }
            });
        });
        
        // Cerrar dropdowns al hacer clic fuera
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.nav-dropdown')) {
                document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
                    menu.classList.remove('show');
                    // Resetear iconos
                    const toggle = document.querySelector(`.dropdown-toggle[data-dropdown="${menu.id.replace('DropdownMenu', '')}"]`);
                    if (toggle) {
                        const icon = toggle.querySelector('.dropdown-icon');
                        if (icon) icon.style.transform = 'rotate(0deg)';
                    }
                });
            }
        });
        
        // Cuando el sidebar se colapsa, cerrar los dropdowns
        document.getElementById('sidebarToggle')?.addEventListener('click', () => {
            document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
                menu.classList.remove('show');
                const toggle = document.querySelector(`.dropdown-toggle[data-dropdown="${menu.id.replace('DropdownMenu', '')}"]`);
                if (toggle) {
                    const icon = toggle.querySelector('.dropdown-icon');
                    if (icon) icon.style.transform = 'rotate(0deg)';
                }
            });
        });
    }
};

// ===== MENSAJES DJANGO =====
const DjangoMessages = {
    init() {
        const messagesScript = document.getElementById('django-messages');
        if (!messagesScript) return;
        
        try {
            const messages = JSON.parse(messagesScript.textContent);
            messages.forEach(msg => {
                let type = 'info';
                if (msg.tags.includes('success')) type = 'success';
                else if (msg.tags.includes('error') || msg.tags.includes('danger')) type = 'error';
                else if (msg.tags.includes('warning')) type = 'warning';
                setTimeout(() => {
                    Toast.show(msg.text, type, 5000);
                }, 100);
            });
        } catch (e) {
            console.error('Error parsing Django messages:', e);
        }
    }
};

// ===== INICIALIZACIÓN =====
document.addEventListener('DOMContentLoaded', () => {
    ThemeManager.init();
    SidebarManager.init();
    SidebarDropdown.init();
    GlobalSearch.init();
    NotificationDropdown.init();
    DjangoMessages.init();
    
    // Agregar estilos de animación dinámicamente
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
        
        @keyframes scaleIn {
            from {
                transform: scale(0.9);
                opacity: 0;
            }
            to {
                transform: scale(1);
                opacity: 1;
            }
        }
        
        .modal-header {
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border-color);
        }
        
        .modal-header h3 {
            color: var(--text-primary);
            font-size: 1.25rem;
        }
        
        .modal-body {
            margin-bottom: 20px;
            color: var(--text-secondary);
        }
        

        .notification-dropdown { position: relative; display: inline-block; }
        .notification-menu { display: none; position: absolute; top: 100%; right: 0; width: 340px; max-height: 400px; overflow-y: auto; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 1000; margin-top: 8px; }
        .notification-menu.show { display: block; }
        .notification-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid var(--border-color); }
        .notification-header h4 { margin: 0; color: var(--text-primary); font-size: 0.95rem; }
        .notification-list { padding: 8px 0; }
        .notification-item { display: flex; align-items: flex-start; gap: 12px; padding: 12px 16px; color: var(--text-primary); text-decoration: none; transition: background 0.2s; }
        .notification-item:hover { background: var(--bg-hover); }
        .notification-icon { font-size: 1.1rem; margin-top: 2px; }
        .notification-content { flex: 1; }
        .notification-content strong { display: block; font-size: 0.85rem; color: var(--text-primary); }
        .notification-content span { display: block; font-size: 0.8rem; color: var(--text-secondary); margin-top: 2px; }
        .notification-empty { text-align: center; padding: 30px 16px; color: var(--text-muted); }
        .header-icon-btn { position: relative; }
        .badge { position: absolute; top: -5px; right: -5px; background: var(--danger); color: white; border-radius: 50%; padding: 2px 8px; font-size: 0.75rem; font-weight: bold; }

        .modal-footer {
            display: flex;
            gap: 12px;
            justify-content: flex-end;
        }
    `;
    document.head.appendChild(style);
});

// ===== UTILIDADES =====
const Utils = {
    formatCurrency(amount) {
        return new Intl.NumberFormat('es-MX', {
            style: 'currency',
            currency: 'MXN'
        }).format(amount);
    },
    
    formatDate(date) {
        return new Intl.DateTimeFormat('es-MX', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        }).format(new Date(date));
    },
    
    formatDateTime(date) {
        return new Intl.DateTimeFormat('es-MX', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(new Date(date));
    }
};

// Exponer utilidades globalmente
window.Toast = Toast;
window.ConfirmModal = ConfirmModal;
window.Utils = Utils;