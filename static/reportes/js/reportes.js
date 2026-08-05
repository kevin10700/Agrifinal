(() => {
    'use strict';

    const reportsPanel = document.getElementById('reports-panel');
    const reportsToggle = document.getElementById('reports-toggle');

    if (!reportsPanel || !reportsToggle) return;

    function setReportsOpen(open) {
        reportsPanel.classList.toggle('is-open', open);
        reportsPanel.setAttribute('aria-hidden', String(!open));
        reportsToggle.setAttribute('aria-expanded', String(open));
        reportsToggle.querySelector('span:last-child').textContent = open ? 'Cerrar reportes' : 'Reportes';
    }

    reportsToggle.addEventListener('click', () => setReportsOpen(!reportsPanel.classList.contains('is-open')));
})();