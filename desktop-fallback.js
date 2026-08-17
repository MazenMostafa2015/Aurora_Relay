(function () {
  "use strict";

  const status = document.getElementById("status");
  const detail = document.getElementById("detail");
  const attempts = 12;
  const delayMs = 1000;

  async function checkService() {
    for (let attempt = 1; attempt <= attempts; attempt += 1) {
      try {
        const response = await fetch("/health", { cache: "no-store", credentials: "same-origin" });
        if (response.ok) {
          status.className = "ready";
          status.lastElementChild.textContent = "Local service is ready";
          detail.textContent = "The secure local service is running. Return to the Aurora Relay desktop workspace; this fallback page does not reload itself or contact third-party services.";
          return;
        }
      } catch (_) {
        // The backend is still starting. Do not send diagnostics anywhere.
      }
      await new Promise(function (resolve) { window.setTimeout(resolve, delayMs); });
    }

    status.className = "failed";
    status.lastElementChild.textContent = "Local service did not respond";
    detail.textContent = "Restart Aurora Relay. If this continues, review the local application logs and do not expose the local service to the network.";
  }

  void checkService();
})();
