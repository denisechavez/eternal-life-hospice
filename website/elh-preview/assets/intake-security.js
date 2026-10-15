// Shared by every intake entry point, including chat. No contact data is sent
// to the bot-verification provider.
let turnstileScript;
function loadTurnstile() {
  if (window.turnstile) return Promise.resolve();
  if (!turnstileScript) {
    turnstileScript = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
      script.async = true;
      const timer = window.setTimeout(() => {
        script.remove();
        reject(new Error("Bot verification could not load."));
      }, 15000);
      script.onload = () => {window.clearTimeout(timer);resolve();};
      script.onerror = () => {
        window.clearTimeout(timer);
        script.remove();
        reject(new Error("Bot verification could not load."));
      };
      document.head.appendChild(script);
    }).catch(error => { turnstileScript = null; throw error; });
  }
  return turnstileScript;
}

async function challenge(siteKey, form) {
  if (!siteKey) return "";
  await loadTurnstile();
  const container = document.createElement("div");
  container.setAttribute("aria-label", "Spam protection");
  container.style.margin = "12px 0";
  (form || document.body).appendChild(container);
  let widget;
  let timer;
  try {
    return await new Promise((resolve, reject) => {
      timer = window.setTimeout(() => reject(new Error("Bot verification timed out.")), 120000);
      widget = window.turnstile.render(container, {
        sitekey: siteKey, action: "intake", appearance: "interaction-only",
        callback: resolve,
        "error-callback": () => reject(new Error("Bot verification failed.")),
        "expired-callback": () => reject(new Error("Bot verification expired."))
      });
    });
  } finally {
    window.clearTimeout(timer);
    if (widget !== undefined) window.turnstile.remove(widget);
    container.remove();
  }
}

export async function submit(options, form) {
  const body = options.body instanceof FormData
    ? options.body : new URLSearchParams(options.body);
  const response = await fetch("/api/form-security?form=" + encodeURIComponent(body.get("form-name") || ""), {
    credentials: "same-origin", cache: "no-store", headers: {Accept: "application/json"}
  });
  if (!response.ok) throw new Error("Secure form verification is unavailable.");
  const security = await response.json();
  const [verification] = await Promise.all([
    challenge(security.siteKey, form),
    new Promise(resolve => window.setTimeout(resolve, security.waitMs + 100))
  ]);
  body.set("_elh_security", security.token);
  if (verification) body.set("cf-turnstile-response", verification);
  return fetch("/api/form-submit", {
    ...options, credentials: "same-origin",
    body: body instanceof FormData ? body : body.toString()
  });
}
