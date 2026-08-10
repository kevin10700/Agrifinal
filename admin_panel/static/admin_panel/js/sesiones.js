/**
 * ===== GESTIÓN DE SESIONES - JAVASCRIPT =====
 * Funcionalidades para el panel de gestión de sesiones
 */

(function() {
    'use strict';

    // ===== CONFIGURACIÓN =====
    const CONFIG = {
        autoRedirectTime: 300000, // 5 minutos en ms
        animationDuration: 300,
        confirmMessages: {
            cerrarTodas: '¿Estás seguro de cerrar TODAS las sesiones? Todos los usuarios deberán iniciar sesión de nuevo.',
            cerrarUsuario: (nombre) => `¿Cerrar TODAS las sesiones de ${nombre}?`,
            cerrarDispositivo: (nombre, ip, dispositivo) => 
                `¿Cerrar esta sesión de ${nombre}?\n\nIP: ${ip}\nDispositivo: ${dispositivo}`
        }
    };

    // ===== INICIALIZACIÓN =====
    document.addEventListener('DOMContentLoaded', function() {
        initSesionesTable();
        initConfirmations();
        initLoadingStates();
        initTooltips();
    });

    // ===== FUNCIONES DE TABLA =====
    function initSesionesTable() {
        const table = document.querySelector('.sesiones-table');
        if (!table) return;

        // Agregar data-labels a las celdas para responsive
        const headers = table.querySelectorAll('thead th');
        const rows = table.querySelectorAll('tbody tr');

        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            cells.forEach((cell, index) => {
                if (headers[index]) {
                    cell.setAttribute('data-label', headers[index].textContent);
                }
            });
        });

        // Ordenar tabla por fecha de login (más reciente primero)
        sortTableByDate(table);
    }

    function sortTableByDate(table) {
        const tbody = table.querySelector('tbody');
        if (!tbody) return;

        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        rows.sort((a, b) => {
            const dateA = new Date(a.querySelector('td:nth-child(5)').textContent);
            const dateB = new Date(b.querySelector('td:nth-child(5)').textContent);
            return dateB - dateA;
        });

        rows.forEach(row => tbody.appendChild(row));
    }

    // ===== CONFIRMACIONES =====
    function initConfirmations() {
        // Botón de cerrar todas las sesiones
        const btnCerrarTodas = document.querySelector('form[action*="cerrar-todas"]');
        if (btnCerrarTodas) {
            btnCerrarTodas.addEventListener('submit', function(e) {
                if (!confirm(CONFIG.confirmMessages.cerrarTodas)) {
                    e.preventDefault();
                }
            });
        }

        // Botones de cerrar sesión de usuario
        document.querySelectorAll('form[action*="cerrar-usuario"]').forEach(form => {
            form.addEventListener('submit', function(e) {
                const nombre = this.querySelector('button')?.getAttribute('title') || 'este usuario';
                if (!confirm(CONFIG.confirmMessages.cerrarUsuario(nombre))) {
                    e.preventDefault();
                }
            });
        });

        // Botones de cerrar dispositivo específico
        document.querySelectorAll('form[action*="cerrar-dispositivo"]').forEach(form => {
            form.addEventListener('submit', function(e) {
                const button = this.querySelector('button');
                const title = button?.getAttribute('title') || '';
                const nombre = 'este usuario';
                const ip = this.closest('tr')?.querySelector('.ip-code')?.textContent || 'N/A';
                const dispositivo = this.closest('tr')?.querySelector('.user-agent-text')?.textContent || 'N/A';
                
                if (!confirm(CONFIG.confirmMessages.cerrarDispositivo(nombre, ip, dispositivo))) {
                    e.preventDefault();
                }
            });
        });
    }

    // ===== ESTADOS DE CARGA =====
    function initLoadingStates() {
        // Agregar loading a botones de acción
        document.querySelectorAll('form[action*="cerrar-"]').forEach(form => {
            form.addEventListener('submit', function() {
                const button = this.querySelector('button[type="submit"]');
                if (button) {
                    const originalContent = button.innerHTML;
                    button.disabled = true;
                    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
                    
                    // Restaurar después de 3 segundos (por si hay error)
                    setTimeout(() => {
                        button.disabled = false;
                        button.innerHTML = originalContent;
                    }, 3000);
                }
            });
        });
    }

    // ===== TOOLTIPS =====
    function initTooltips() {
        // Inicializar tooltips de Bootstrap si están disponibles
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            const tooltipTriggerList = [].slice.call(
                document.querySelectorAll('[data-bs-toggle="tooltip"]')
            );
            tooltipTriggerList.map(function(tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }

        // Tooltip personalizado para User-Agent completo
        document.querySelectorAll('.user-agent-text').forEach(element => {
            element.setAttribute('title', element.textContent);
            element.style.cursor = 'pointer';
            
            element.addEventListener('mouseenter', function() {
                this.style.transform = 'scale(1.05)';
                this.style.zIndex = '1000';
                this.style.position = 'relative';
            });
            
            element.addEventListener('mouseleave', function() {
                this.style.transform = 'scale(1)';
                this.style.zIndex = '1';
            });
        });
    }

    // ===== UTILIDADES =====
    
    // Formatear fecha relativa (hace X tiempo)
    function formatRelativeDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (minutes < 1) return 'Hace un momento';
        if (minutes < 60) return `Hace ${minutes} minuto${minutes > 1 ? 's' : ''}`;
        if (hours < 24) return `Hace ${hours} hora${hours > 1 ? 's' : ''}`;
        if (days < 7) return `Hace ${days} día${days > 1 ? 's' : ''}`;
        
        return date.toLocaleDateString('es-MX');
    }

    // Actualizar tiempos relativos cada minuto
    setInterval(() => {
        document.querySelectorAll('.login-time').forEach(element => {
            const dateString = element.getAttribute('data-date');
            if (dateString) {
                element.textContent = formatRelativeDate(dateString);
            }
        });
    }, 60000);

    // ===== EXPORTAR FUNCIONES =====
    window.SesionesManager = {
        formatRelativeDate,
        sortTableByDate,
        initSesionesTable
    };

})();