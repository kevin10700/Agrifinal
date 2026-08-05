// static/chatbot/js/admin_chatbot.js
// Lógica del chat de administración. A diferencia de chatbot.js (cliente),
// este envía FormData porque puede incluir una imagen adjunta.

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("admin-chat-form");
    const input = document.getElementById("admin-chat-input");
    const inputImagen = document.getElementById("admin-chat-imagen");
    const preview = document.getElementById("preview-imagen");
    const mensajesDiv = document.getElementById("admin-chat-mensajes");
    const btnEnviar = document.getElementById("admin-chat-enviar");
    const btnMicrofono = document.getElementById("admin-chat-microfono");

    let archivoSeleccionado = null;

    function agregarMensaje(texto, tipo) {
        const div = document.createElement("div");
        div.className = `msg ${tipo}`;
        div.textContent = texto;
        mensajesDiv.appendChild(div);
        mensajesDiv.scrollTop = mensajesDiv.scrollHeight;
    }

    function enviarFormulario() {
        if (input.value.trim()) form.requestSubmit();
    }

    inputImagen.addEventListener("change", () => {
        const archivo = inputImagen.files[0];
        if (archivo) {
            archivoSeleccionado = archivo;
            preview.src = URL.createObjectURL(archivo);
            preview.style.display = "inline-block";
        }
    });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const mensaje = input.value.trim();
        if (!mensaje) return;

        agregarMensaje(mensaje, "usuario");
        input.value = "";
        btnEnviar.disabled = true;

        const formData = new FormData();
        formData.append("mensaje", mensaje);
        if (archivoSeleccionado) {
            formData.append("imagen", archivoSeleccionado);
        }

        const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;

        try {
            const response = await fetch(window.ADMIN_CHAT_URL, {
                method: "POST",
                headers: { "X-CSRFToken": csrfToken },
                body: formData,
            });
            const data = await response.json();
            agregarMensaje(data.respuesta || "Sin respuesta.", "bot");
        } catch (err) {
            agregarMensaje("Error de conexión con el asistente.", "bot");
        } finally {
            // Limpiamos la imagen adjunta después de cada envío
            archivoSeleccionado = null;
            inputImagen.value = "";
            preview.style.display = "none";
            btnEnviar.disabled = false;
        }
    });

    // Reconocimiento de voz del navegador. No graba ni guarda audio en el servidor:
    // únicamente coloca la transcripción en el campo para que el administrador la revise.
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        btnMicrofono.disabled = true;
        btnMicrofono.title = "Tu navegador no admite reconocimiento de voz. Usa Chrome o Edge.";
    } else {
        const reconocimiento = new SpeechRecognition();
        reconocimiento.lang = "es-MX";
        reconocimiento.continuous = false;
        reconocimiento.interimResults = true;
        let textoInicial = "";
        let enviarAlTerminar = false;

        function actualizarMicrofono(escuchando) {
            btnMicrofono.classList.toggle("escuchando", escuchando);
            btnMicrofono.setAttribute("aria-pressed", String(escuchando));
            btnMicrofono.title = escuchando ? "Detener escucha" : "Dictar instrucción por voz";
            // El icono se actualiza vía MutationObserver en la plantilla del panel,
            // que reemplaza el emoji por iconos Font Awesome. Mantenemos un fallback
            // con textContent para compatibilidad con la plantilla iframe original.
            if (!btnMicrofono.querySelector('i')) {
                btnMicrofono.textContent = escuchando ? "⏹" : "🎙️";
            }
        }

        btnMicrofono.addEventListener("click", () => {
            if (btnMicrofono.classList.contains("escuchando")) {
                // Segundo toque: detener el dictado y ejecutar la instrucción.
                enviarAlTerminar = true;
                reconocimiento.stop();
                return;
            }
            textoInicial = input.value.trim();
            enviarAlTerminar = false;
            try {
                reconocimiento.start();
            } catch (_) {
                // Algunos navegadores lanzan error si aún está cerrando una escucha anterior.
            }
        });

        reconocimiento.onstart = () => actualizarMicrofono(true);
        reconocimiento.onend = () => {
            actualizarMicrofono(false);
            if (enviarAlTerminar && input.value.trim()) {
                enviarAlTerminar = false;
                enviarFormulario();
            }
        };
        reconocimiento.onresult = (event) => {
            let transcripcion = "";
            for (let i = event.resultIndex; i < event.results.length; i += 1) {
                transcripcion += event.results[i][0].transcript;
            }
            input.value = [textoInicial, transcripcion.trim()].filter(Boolean).join(textoInicial && transcripcion.trim() ? " " : "");
            input.focus();
        };
        reconocimiento.onerror = (event) => {
            actualizarMicrofono(false);
            enviarAlTerminar = false;
            if (event.error === "not-allowed" || event.error === "service-not-allowed") {
                agregarMensaje("No se concedió permiso para usar el micrófono. Actívalo en el navegador e inténtalo de nuevo.", "bot");
            } else if (event.error !== "aborted" && event.error !== "no-speech") {
                agregarMensaje("No pude transcribir el audio. Inténtalo otra vez.", "bot");
            }
        };
    }

    // El iframe recibe los colores calculados del admin padre, incluidos los del modo oscuro.
    window.addEventListener("message", (event) => {
        if (event.origin !== window.location.origin || event.data?.type !== "agrivale-admin-theme") return;
        Object.entries(event.data.variables || {}).forEach(([name, value]) => {
            if (value) document.documentElement.style.setProperty(name, value);
        });
    });
});
