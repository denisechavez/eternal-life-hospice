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

const failureMessages = {
  verification: "We couldn't complete the security check, so your request has not been sent. Your information is still here. You can try the security check again or call our care team.",
  rejected: "Your request was not accepted. Your information is still here. Please call our care team for help before trying again.",
  unknown: "We couldn't confirm whether your request was received. To avoid a duplicate request, please call our care team to confirm receipt before sending another request. Your information is still here."
};

function submissionError(outcome) {
  const error = new Error(failureMessages[outcome]);
  error.intakeOutcome = outcome;
  return error;
}

// Fixed, local copy only: never display server/provider messages or submitted data.
export function showFailure(error, container) {
  const outcome = error && error.intakeOutcome || "unknown";
  container.textContent = failureMessages[outcome] || failureMessages.unknown;
  const cta = document.createElement("div");
  cta.innerHTML = '<p>Need to speak with someone now?</p><p>We&#x27;re here for you 24 hours a day, 7 days a week.</p><p><a href="tel:18059537273">Call 805.953.7273</a></p>';
  container.appendChild(cta);
  return outcome;
}

export async function submit(options, form) {
  const body = options.body instanceof FormData
    ? options.body : new URLSearchParams(options.body);
  try {
    const response = await fetch("/api/form-security?form=" + encodeURIComponent(body.get("form-name") || ""), {
      credentials: "same-origin", cache: "no-store", headers: {Accept: "application/json"}
    });
    if (!response.ok) throw new Error("Security unavailable");
    const security = await response.json();
    if (!security || typeof security.token !== "string" || !security.token ||
        !Number.isFinite(security.waitMs) || security.waitMs < 0) {
      throw new Error("Invalid security response");
    }
    const [verification] = await Promise.all([
      challenge(security.siteKey, form),
      new Promise(resolve => window.setTimeout(resolve, security.waitMs + 100))
    ]);
    body.set("_elh_security", security.token);
    if (verification) body.set("cf-turnstile-response", verification);
  } catch (_) {
    throw submissionError("verification");
  }
  let response, data;
  try {
    response = await fetch("/api/form-submit", {
      ...options, credentials: "same-origin",
      body: body instanceof FormData ? body : body.toString()
    });
    data = await response.clone().json();
  } catch (_) {
    // POST may already have reached intake. Never retry or claim non-delivery.
    throw submissionError("unknown");
  }
  if (response.ok && data && data.ok === true && data.accepted === true) return response;
  // A generic 5xx may follow delivery; only an explicit rejection is definitive.
  if (data && data.ok === false && data.accepted !== true &&
      (data.accepted === false || response.status < 500 || data.error === "security_unavailable")) {
    throw submissionError("rejected");
  }
  throw submissionError("unknown");
}
