document.addEventListener("DOMContentLoaded", function() {
    // Cerrar alertas automáticamente después de 4 segundos
    document.querySelectorAll('.dismissible-alert').forEach(function(alert) {
        window.setTimeout(function() {
            alert.classList.add('toast-leave');
            window.setTimeout(function() { new bootstrap.Alert(alert).close(); }, 250);
        }, 4000);
    });

    // Tutorial de onboarding
    const shouldTour = window.agrivaleConfig.isAuthenticated &&
        window.agrivaleConfig.isNewUser && !localStorage.getItem('agrivale_onboarding_completado');
    const finishTour = function() {
        localStorage.setItem('agrivale_onboarding_completado', 'true');
        fetch('/usuarios/onboarding/completar/', {method: 'POST', headers: {'X-CSRFToken': window.agrivaleConfig.csrfToken}}).catch(function() {});
        const skip = document.getElementById('saltar-tutorial'); if (skip) skip.remove();
    };
    window.iniciarTutorialAgrivale = function(force) {
        if (!force && !shouldTour) return;
        const driverObj = window.driver && window.driver.js.driver({
            showProgress: true, allowClose: true,
            nextBtnText: 'Siguiente', prevBtnText: 'Anterior', doneBtnText: 'Finalizar',
            onDestroyed: finishTour,
            steps: [
                {popover: {title: 'Bienvenido', description: 'Bienvenido a Agrivale - Tu tienda de insumos para siembra'}},
                {element: '.producto-card', popover: {title: 'Catálogo', description: 'Aquí encontrarás nuestro catálogo de insumos agrícolas: semillas, fertilizantes, abonos, agroquímicos, riego y herramientas.'}},
                {element: '#buscador-productos', popover: {title: 'Busca por cultivo', description: 'Usa el buscador para filtrar por cultivo: maíz, jitomate, etc.'}},
                {element: '.producto-card', popover: {title: 'Compra', description: 'Agrega al carrito y selecciona presentación (1kg, 5kg, 25kg)'}},
                {element: '#carrito-nav', popover: {title: 'Tu carrito', description: 'Aquí ves tu carrito, envíos y facturación'}},
                {element: '#chatbot-toggle, .chatbot-toggle', popover: {title: 'Ayuda', description: '¿Necesitas ayuda? Usa el chatbot agrícola abajo a la derecha'}}
            ]
        });
        if (driverObj) { window.agrivaleDriver = driverObj; driverObj.drive(); }
    };
    if (shouldTour) window.iniciarTutorialAgrivale(false);

    // Funcionalidad de accesibilidad
    const btnAccesibilidad = document.getElementById('btn-accesibilidad');
    const panelAccesibilidad = document.getElementById('panel-accesibilidad');
    const sliderTamano = document.getElementById('slider-tamano');
    const tamanoValor = document.getElementById('tamano-valor');
    const btnModoClaro = document.getElementById('btn-modo-claro');
    const btnModoOscuro = document.getElementById('btn-modo-oscuro');
    const body = document.body;

    // Aplicar preferencias guardadas
    const tamanoGuardado = localStorage.getItem('agrivale_tamano_fuente');
    const modoGuardado = localStorage.getItem('agrivale_modo');

    if (tamanoGuardado) {
        body.style.fontSize = tamanoGuardado + 'px';
        sliderTamano.value = tamanoGuardado;
        tamanoValor.textContent = tamanoGuardado + 'px';
    }

    if (modoGuardado === 'oscuro') {
        body.classList.add('modo-oscuro');
        btnModoClaro.classList.remove('active');
        btnModoOscuro.classList.add('active');
    }

    // Toggle del panel de accesibilidad
    if (btnAccesibilidad) {
        btnAccesibilidad.addEventListener('click', function(e) {
            e.stopPropagation();
            panelAccesibilidad.classList.toggle('mostrar');
        });
    }

    // Cerrar panel al hacer clic fuera
    document.addEventListener('click', function(e) {
        if (!panelAccesibilidad.contains(e.target) && e.target !== btnAccesibilidad) {
            panelAccesibilidad.classList.remove('mostrar');
        }
    });

    // Control de tamaño de fuente
    if (sliderTamano) {
        sliderTamano.addEventListener('input', function() {
            const tamano = this.value;
            body.style.fontSize = tamano + 'px';
            tamanoValor.textContent = tamano + 'px';
            localStorage.setItem('agrivale_tamano_fuente', tamano);
        });
    }

    // Modo claro
    if (btnModoClaro) {
        btnModoClaro.addEventListener('click', function() {
            body.classList.remove('modo-oscuro');
            btnModoClaro.classList.add('active');
            btnModoOscuro.classList.remove('active');
            localStorage.setItem('agrivale_modo', 'claro');
        });
    }

    // Modo oscuro
    if (btnModoOscuro) {
        btnModoOscuro.addEventListener('click', function() {
            body.classList.add('modo-oscuro');
            btnModoOscuro.classList.add('active');
            btnModoClaro.classList.remove('active');
            localStorage.setItem('agrivale_modo', 'oscuro');
        });
    }
});
