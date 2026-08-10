/**
 * ===== HISTORIAL DE PRODUCTOS - JAVASCRIPT =====
 * Funcionalidades para el panel de historial de productos
 */

(function() {
    'use strict';

    // ===== CONFIGURACIÓN =====
    const CONFIG = {
        animationDuration: 500,
        autoLoadMore: false,
        itemsPerLoad: 20
    };

    // ===== INICIALIZACIÓN =====
    document.addEventListener('DOMContentLoaded', function() {
        initTimeline();
        initFilters();
        initStats();
        initTooltips();
    });

    // ===== TIMELINE =====
    function initTimeline() {
        const timeline = document.querySelector('.timeline');
        if (!timeline) return;

        // Agregar clases de animación a los items
        const items = timeline.querySelectorAll('.timeline-item');
        items.forEach((item, index) => {
            item.style.animationDelay = `${index * 0.1}s`;
        });

        // Scroll reveal para items del timeline
        initScrollReveal();
    }

    function initScrollReveal() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });

        document.querySelectorAll('.timeline-item').forEach(item => {
            item.style.opacity = '0';
            item.style.transform = 'translateY(20px)';
            item.style.transition = `opacity ${CONFIG.animationDuration}ms ease, transform ${CONFIG.animationDuration}ms ease`;
            observer.observe(item);
        });
    }

    // ===== FILTROS =====
    function initFilters() {
        // Auto-submit en selects de filtro
        const filterSelects = document.querySelectorAll('.filtro-select');
        filterSelects.forEach(select => {
            select.addEventListener('change', function() {
                // Agregar loading
                showLoading();
                
                // Submit del formulario
                this.closest('form')?.submit();
            });
        });

        // Botón de limpiar filtros
        const btnLimpiar = document.querySelector('.btn-limpiar-filtros');
        if (btnLimpiar) {
            btnLimpiar.addEventListener('click', function(e) {
                e.preventDefault();
                
                // Limpiar todos los selects
                filterSelects.forEach(select => {
                    select.value = '';
                });
                
                // Redirigir sin filtros
                const url = new URL(window.location.href);
                url.search = '';
                window.location.href = url.toString();
            });
        }

        // Remover filtros individuales
        document.querySelectorAll('.remove-filter').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const filterName = this.getAttribute('data-filter');
                const filterValue = this.getAttribute('data-value');
                
                // Remover el filtro
                const url = new URL(window.location.href);
                url.searchParams.delete(filterName);
                window.location.href = url.toString();
            });
        });
    }

    // ===== ESTADÍSTICAS =====
    function initStats() {
        // Animar contadores de estadísticas
        const statCards = document.querySelectorAll('.stat-card-historial');
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const valueElement = entry.target.querySelector('.stat-value');
                    if (valueElement && !valueElement.dataset.animated) {
                        const finalValue = parseInt(valueElement.textContent);
                        animateCounter(valueElement, 0, finalValue, 1000);
                        valueElement.dataset.animated = 'true';
                    }
                }
            });
        }, { threshold: 0.5 });

        statCards.forEach(card => observer.observe(card));
    }

    function animateCounter(element, start, end, duration) {
        const range = end - start;
        const increment = range / (duration / 16);
        let current = start;

        const timer = setInterval(() => {
            current += increment;
            if (current >= end) {
                element.textContent = end;
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current);
            }
        }, 16);
    }

    // ===== TOOLTIPS =====
    function initTooltips() {
        // Inicializar tooltips de Bootstrap
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            const tooltipTriggerList = [].slice.call(
                document.querySelectorAll('[data-bs-toggle="tooltip"]')
            );
            tooltipTriggerList.map(function(tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }

        // Tooltip para valores de cambio
        document.querySelectorAll('.cambio-valor').forEach(element => {
            element.setAttribute('title', element.textContent);
            element.style.cursor = 'help';
        });

        // Tooltip para porcentajes
        document.querySelectorAll('.cambio-porcentaje').forEach(element => {
            const valor = element.textContent;
            element.setAttribute('title', `Cambio: ${valor}`);
        });
    }

    // ===== UTILIDADES =====

    // Mostrar loading
    function showLoading() {
        const loader = document.createElement('div');
        loader.className = 'loading-overlay';
        loader.innerHTML = `
            <div class="spinner"></div>
        `;
        document.body.appendChild(loader);

        // Remover después de 2 segundos (por si hay error)
        setTimeout(() => {
            loader.remove();
        }, 2000);
    }

    // Formatear número con separadores de miles
    function formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }

    // Formatear moneda
    function formatCurrency(amount, currency = 'MXN') {
        return new Intl.NumberFormat('es-MX', {
            style: 'currency',
            currency: currency
        }).format(amount);
    }

    // Formatear porcentaje
    function formatPercentage(value, decimals = 2) {
        return `${value.toFixed(decimals)}%`;
    }

    // Calcular diferencia porcentual
    function calculatePercentageChange(oldValue, newValue) {
        if (oldValue === 0) return 0;
        return ((newValue - oldValue) / oldValue) * 100;
    }

    // Determinar clase de color según el cambio
    function getChangeClass(oldValue, newValue) {
        if (newValue > oldValue) return 'positive';
        if (newValue < oldValue) return 'negative';
        return 'neutral';
    }

    // Obtener icono según tipo de cambio
    function getIconForTipo(tipo) {
        const icons = {
            'creacion': 'fa-plus-circle',
            'precio': 'fa-dollar-sign',
            'stock': 'fa-boxes',
            'estado': 'fa-toggle-on',
            'compra': 'fa-shopping-cart',
            'pedido': 'fa-shopping-bag'
        };
        return icons[tipo] || 'fa-circle';
    }

    // Obtener color según tipo de cambio
    function getColorForTipo(tipo) {
        const colors = {
            'creacion': '#28a745',
            'precio': '#ffc107',
            'stock': '#17a2b8',
            'estado': '#dc3545',
            'compra': '#28a745',
            'pedido': '#007bff'
        };
        return colors[tipo] || '#667eea';
    }

    // ===== LAZY LOADING (Opcional) =====
    function initLazyLoading() {
        if (!CONFIG.autoLoadMore) return;

        const timeline = document.querySelector('.timeline');
        if (!timeline) return;

        let loading = false;
        let page = 1;

        const loadMore = () => {
            if (loading) return;
            loading = true;

            // Aquí iría la lógica para cargar más items
            // Por ahora solo es un placeholder
            console.log('Loading more items...');
        };

        // Scroll infinito
        window.addEventListener('scroll', () => {
            const scrollPosition = window.innerHeight + window.scrollY;
            const threshold = document.body.offsetHeight - 500;

            if (scrollPosition >= threshold) {
                loadMore();
            }
        });
    }

    // ===== EXPORTAR FUNCIONES =====
    window.HistorialManager = {
        formatNumber,
        formatCurrency,
        formatPercentage,
        calculatePercentageChange,
        getChangeClass,
        getIconForTipo,
        getColorForTipo
    };

})();