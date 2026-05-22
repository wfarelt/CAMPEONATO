(() => {
  const button = document.getElementById("enable-push-btn");
  const statusText = document.getElementById("push-status-text");
  const configElement = document.getElementById("web-push-config");
  const publicKeyElement = document.getElementById("web-push-public-key");

  if (!button || !statusText || !configElement || !publicKeyElement) {
    return;
  }

  const config = JSON.parse(configElement.textContent || "{}");
  const publicKey = JSON.parse(publicKeyElement.textContent || '""');

  const setStatus = (text) => {
    statusText.textContent = text;
  };

  const setButton = ({ text, disabled = false, primary = true }) => {
    button.disabled = disabled;
    button.textContent = text;
    button.classList.toggle("bg-primary", primary);
    button.classList.toggle("hover:bg-primary/90", primary);
    button.classList.toggle("bg-[#282e39]", !primary);
    button.classList.toggle("hover:bg-[#343b48]", !primary);
  };

  const urlBase64ToUint8Array = (base64String) => {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; i += 1) {
      outputArray[i] = rawData.charCodeAt(i);
    }

    return outputArray;
  };

  const postJson = async (url, payload) => {
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": config.csrfToken,
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    return response.json();
  };

  const initPush = async () => {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
      setStatus("Este navegador no soporta notificaciones push web.");
      setButton({ text: "No compatible", disabled: true });
      return;
    }

    if (!publicKey) {
      setStatus("Falta configurar la llave publica VAPID en el servidor.");
      setButton({ text: "Configuracion pendiente", disabled: true });
      return;
    }

    if (Notification.permission === "denied") {
      setStatus("Permiso denegado. Debes habilitar notificaciones desde la configuracion del navegador.");
      setButton({ text: "Permiso denegado", disabled: true });
      return;
    }

    const registration = await navigator.serviceWorker.register(config.serviceWorkerUrl, {
      scope: "/",
    });

    const existingSubscription = await registration.pushManager.getSubscription();

    if (existingSubscription) {
      setStatus("Este dispositivo ya esta suscrito a notificaciones push.");
      setButton({ text: "Desactivar notificaciones", primary: false });

      button.onclick = async () => {
        try {
          await postJson(config.unsubscribeUrl, { endpoint: existingSubscription.endpoint });
          await existingSubscription.unsubscribe();
          setStatus("Notificaciones desactivadas para este dispositivo.");
          setButton({ text: "Activar notificaciones", primary: true });
          button.onclick = null;
          await initPush();
        } catch (error) {
          setStatus("No se pudo desactivar la suscripcion push.");
        }
      };
      return;
    }

    if (Notification.permission === "granted") {
      setStatus("Permiso concedido. Pulsa para completar la suscripcion push.");
    } else {
      setStatus("Activa notificaciones para recibir avisos aunque cierres la pagina.");
    }

    setButton({ text: "Activar notificaciones", primary: true });

    button.onclick = async () => {
      try {
        const permission = await Notification.requestPermission();
        if (permission !== "granted") {
          setStatus("No se concedio el permiso de notificaciones.");
          setButton({ text: "Permiso no concedido", disabled: true });
          return;
        }

        const subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(publicKey),
        });

        await postJson(config.subscribeUrl, { subscription: subscription.toJSON() });
        setStatus("Notificaciones push activadas correctamente.");
        setButton({ text: "Ya suscrito", disabled: true });
      } catch (error) {
        setStatus("Error al activar notificaciones push. Revisa HTTPS y configuracion VAPID.");
      }
    };
  };

  initPush().catch(() => {
    setStatus("No fue posible inicializar las notificaciones push.");
    setButton({ text: "Error de inicializacion", disabled: true });
  });
})();
