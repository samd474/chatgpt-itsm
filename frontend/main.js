const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

document.querySelector("#app").textContent = `ITSM frontend - API: ${apiBaseUrl}`;
