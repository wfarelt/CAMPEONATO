{% load static %}
self.addEventListener("push", (event) => {
  let payload = {};

  if (event.data) {
    try {
      payload = event.data.json();
    } catch (error) {
      payload = {
        title: "Notificacion",
        body: event.data.text(),
      };
    }
  }

  const title = payload.title || "Notificacion";
  const options = {
    body: payload.body || "Tienes una nueva alerta.",
    icon: payload.icon || "{% static 'tournament/img/favicon.png' %}",
    image: payload.image || undefined,
    vibrate: Array.isArray(payload.vibrate) ? payload.vibrate : [120, 60, 120],
    tag: payload.tag || "championship-notification",
    data: {
      url: payload.url || "/notifications/",
    },
    actions: Array.isArray(payload.actions) && payload.actions.length
      ? payload.actions
      : [{ action: "open", title: "Abrir" }],
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  if (event.action === "close") {
    return;
  }

  const targetUrl = event.notification.data && event.notification.data.url
    ? event.notification.data.url
    : "/notifications/";

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.includes(targetUrl) && "focus" in client) {
          return client.focus();
        }
      }

      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }

      return null;
    })
  );
});
