// ============ LÓGICA DEL CHATBOT AGRIVALE ============
// Necesita 2 variables globales definidas en el HTML antes de cargar este script:
//   window.AGRIVALE_CHAT_URL  -> la url del endpoint (ej: "/chatbot/mensaje/")
//   window.AGRIVALE_CSRF_TOKEN -> el token CSRF de Django

document.addEventListener("DOMContentLoaded", function () {
  const toggleBtn = document.getElementById("agrivale-chat-toggle");
  const panel = document.getElementById("agrivale-chat-panel");
  const cerrarBtn = document.getElementById("agrivale-chat-cerrar");
  const mensajesDiv = document.getElementById("agrivale-chat-mensajes");
  const inputTexto = document.getElementById("agrivale-input-texto");
  const enviarBtn = document.getElementById("agrivale-enviar-btn");
  const micBtn = document.getElementById("agrivale-mic-btn");
  const atajos = document.querySelectorAll("#agrivale-chat-atajos [data-mensaje]");

  if (!toggleBtn || !panel) return; // el widget no está en esta página

  // --- Abrir / cerrar panel ---
  function abrirPanel() {
    panel.classList.remove("oculto");
    panel.classList.remove("minimizado");
    toggleBtn.setAttribute("aria-expanded", "true");
    inputTexto.focus();
  }
  function cerrarPanel() {
    panel.classList.add("oculto");
    panel.classList.remove("minimizado");
    toggleBtn.setAttribute("aria-expanded", "false");
  }
  function minimizarPanel() {
    panel.classList.toggle("minimizado");
    // Si estaba oculto, lo mostramos minimizado
    if (panel.classList.contains("oculto")) {
      panel.classList.remove("oculto");
      toggleBtn.setAttribute("aria-expanded", "true");
    }
  }
  toggleBtn.addEventListener("click", () => panel.classList.contains("oculto") ? abrirPanel() : cerrarPanel());
  cerrarBtn.addEventListener("click", cerrarPanel);

  // Botón minimizar
  const minimizarBtn = document.getElementById("agrivale-chat-minimizar");
  if (minimizarBtn) {
    minimizarBtn.addEventListener("click", function(e) {
      e.stopPropagation();
      minimizarPanel();
    });
  }

  // Doble click en header para minimizar en móvil
  const chatHeader = document.getElementById("agrivale-chat-header");
  if (chatHeader) {
    chatHeader.addEventListener("dblclick", minimizarPanel);
  }

  // --- Agregar mensaje a la ventana ---
  function agregarMensaje(texto, tipo) {
    const div = document.createElement("div");
    div.className = "mensaje " + tipo;
    div.textContent = texto;
    mensajesDiv.appendChild(div);
    mensajesDiv.scrollTop = mensajesDiv.scrollHeight;
  }

  // --- Leer respuesta en voz alta ---
  function hablar(texto) {
    if (!("speechSynthesis" in window)) return;
    const utterance = new SpeechSynthesisUtterance(texto);
    utterance.lang = "es-MX";
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  }

  // --- Enviar mensaje al backend ---
  async function enviarMensaje(texto) {
    if (!texto.trim()) return;
    agregarMensaje(texto, "usuario");
    inputTexto.value = "";

    try {
      const resp = await fetch(window.AGRIVALE_CHAT_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": window.AGRIVALE_CSRF_TOKEN,
        },
        body: JSON.stringify({ mensaje: texto }),
      });
      const data = await resp.json();

      agregarMensaje(data.respuesta, "bot");
      hablar(data.respuesta);

      if (data.url) {
        setTimeout(() => { window.location.href = data.url; }, 1200);
      }
    } catch (error) {
      agregarMensaje("Hubo un problema de conexión. Intenta de nuevo.", "bot");
    }
  }

  enviarBtn.addEventListener("click", () => enviarMensaje(inputTexto.value));
  inputTexto.addEventListener("keyup", (e) => {
    if (e.key === "Enter") enviarMensaje(inputTexto.value);
  });
  atajos.forEach((boton) => boton.addEventListener("click", () => enviarMensaje(boton.dataset.mensaje)));

  // --- Reconocimiento de voz (micrófono) ---
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.lang = "es-MX";
    recognition.continuous = false;
    recognition.interimResults = false;

    micBtn.addEventListener("click", () => {
      abrirPanel();
      micBtn.classList.add("escuchando");
      recognition.start();
    });

    recognition.addEventListener("result", (event) => {
      const texto = event.results[0][0].transcript;
      enviarMensaje(texto);
    });

    recognition.addEventListener("end", () => {
      micBtn.classList.remove("escuchando");
    });

    recognition.addEventListener("error", () => {
      micBtn.classList.remove("escuchando");
      agregarMensaje("No pude escucharte bien. Intenta de nuevo o escribe tu pregunta.", "bot");
    });
  } else {
    if (micBtn) micBtn.style.display = "none"; // navegador sin soporte de voz
  }
});
