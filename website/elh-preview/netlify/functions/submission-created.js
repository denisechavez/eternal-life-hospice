/**
 * Eternal Life Hospice — automatic reply to people who reach out.
 *
 * Netlify calls this function automatically every time a form is submitted
 * (the function name "submission-created" is a Netlify convention). We use it
 * to send the person an instant, warm acknowledgement so no one is left
 * wondering whether their message went through.
 *
 * Requires: RESEND_API_KEY (set in the Netlify dashboard, "All scopes").
 *   Sign up free at resend.com, verify the eternallifehospice.com domain, then
 *   add the API key. Without the key, this function quietly does nothing — your
 *   internal team notifications still work exactly as before.
 *
 * Optional: AUTOREPLY_FROM (defaults to the verified sending address below).
 *
 * A reply is only sent when a submission includes a valid email, so it degrades
 * safely. Eligible forms: elh-family, elh-casemanager, elh-careers (collect an
 * email), and elh-physician (the /refer page adds an OPTIONAL work email — when
 * provided, the partner gets a PHI-free referral confirmation; the homepage
 * physician form has no email field and is unaffected). The remaining phone-only
 * forms (elh-coordinator, elh-chat-callback) are never replied to here.
 */

const PHONE = "805.953.7273";
const CONTACT_EMAIL = "info@eternallifehospice.com";
const FROM =
  process.env.AUTOREPLY_FROM ||
  "Eternal Life Hospice <" + CONTACT_EMAIL + ">";

// Forms eligible for an auto-reply. A reply is only ever sent when the submission
// also carries a valid email, so a form is safe to list here even when its email
// field is optional:
//   elh-family, elh-casemanager, elh-careers — collect an email directly.
//   elh-physician — the /refer page adds an OPTIONAL work email; when a partner
//     provides it they get a PHI-free referral confirmation. The homepage
//     physician form has no email field, so it is never affected.
// Still phone-only (never replied to): elh-coordinator, elh-chat-callback.
const ALLOWED_FORMS = ["elh-family", "elh-casemanager", "elh-careers", "elh-physician"];

exports.handler = async function (event) {
  try {
    const apiKey = process.env.RESEND_API_KEY;
    if (!apiKey) {
      // No email service configured yet — skip silently so submissions and
      // internal notifications are never affected.
      return { statusCode: 200, body: "auto-reply not configured; skipped" };
    }

    const body = JSON.parse(event.body || "{}");
    const payload = body.payload || {};
    const data = payload.data || {};
    const formName = payload.form_name || data["form-name"] || "";

    if (ALLOWED_FORMS.indexOf(formName) === -1) {
      return { statusCode: 200, body: "form not eligible for auto-reply; skipped" };
    }

    const toEmail = String(data.email || "").trim().toLowerCase();
    if (!isValidEmail(toEmail)) {
      return { statusCode: 200, body: "no valid email on submission; skipped" };
    }

    // Referrer name (a professional, not the patient — never PHI). Greet by first
    // name only, whichever field the form used.
    const rawName = String(
      data.first_name || data.name || data.referrer_name || ""
    ).trim();
    const firstName = rawName.split(/\s+/)[0] || "";
    const greeting = firstName ? "Hi " + escapeText(firstName) + "," : "Hello,";
    const isCareers = formName === "elh-careers";
    const isReferral = formName === "elh-physician";

    const subject = isCareers
      ? "Thank you for your interest — Eternal Life Hospice"
      : isReferral
      ? "We received your referral — Eternal Life Hospice"
      : "We received your message — Eternal Life Hospice";

    // Static, PHI-free copy. We never echo the submitted clinical description.
    const lead = isCareers
      ? "Thank you for your interest in joining the Eternal Life Hospice team. We've received your application and a member of our team will review it and be in touch."
      : isReferral
      ? "Thank you for referring a patient to Eternal Life Hospice. We've received your referral, and our clinical intake team will reach out shortly to complete the details with you securely by phone. No patient information is ever exchanged by email."
      : "Thank you for reaching out to Eternal Life Hospice. We've received your message, and a member of our team will be in touch with you shortly.";

    const text = [
      greeting,
      "",
      lead,
      "",
      "If you'd like to speak with someone right away, please call us at " +
        PHONE + " — we're here for you.",
      "",
      "With care,",
      "Eternal Life Hospice",
      PHONE,
      CONTACT_EMAIL
    ].join("\n");

    const html = renderHtml(greeting, lead);

    const resp = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: "Bearer " + apiKey,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        from: FROM,
        to: [toEmail],
        reply_to: CONTACT_EMAIL,
        subject: subject,
        text: text,
        html: html
      })
    });

    if (!resp.ok) {
      const detail = await safeText(resp);
      console.error(
        "Auto-reply send failed (" + resp.status + "): " + detail
      );
      // Return 200 so Netlify never marks the submission itself as failed.
      return { statusCode: 200, body: "auto-reply send failed; logged" };
    }

    return { statusCode: 200, body: "auto-reply sent" };
  } catch (e) {
    console.error("Auto-reply error: " + (e && e.message ? e.message : e));
    return { statusCode: 200, body: "auto-reply error; logged" };
  }
};

function renderHtml(greeting, lead) {
  return [
    '<!doctype html><html><body style="margin:0;padding:0;background:#F5F0EB;">',
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F5F0EB;padding:32px 0;">',
    '<tr><td align="center">',
    '<table role="presentation" width="520" cellpadding="0" cellspacing="0" style="max-width:520px;width:100%;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #D8CDBF;">',
    '<tr><td style="background:#5B2E59;padding:22px 32px;">',
    '<div style="font-family:Georgia,\'Times New Roman\',serif;color:#F5F0EB;font-size:20px;letter-spacing:.3px;">Eternal Life Hospice</div>',
    "</td></tr>",
    '<tr><td style="padding:30px 32px;font-family:Georgia,\'Times New Roman\',serif;color:#3C1C3B;font-size:16px;line-height:1.7;">',
    "<p style=\"margin:0 0 16px;\">" + greeting + "</p>",
    "<p style=\"margin:0 0 16px;\">" + lead + "</p>",
    '<p style="margin:0 0 20px;">If you\'d like to speak with someone right away, please call us at ' +
      '<a href="tel:8059537273" style="color:#5B2E59;font-weight:bold;text-decoration:none;">' +
      PHONE + "</a> — we're here for you.</p>",
    '<div style="height:1px;background:#EDE6DE;margin:24px 0;"></div>',
    '<p style="margin:0;color:#6b5f57;font-size:14px;line-height:1.6;">With care,<br>',
    "Eternal Life Hospice<br>",
    '<a href="tel:8059537273" style="color:#5B2E59;text-decoration:none;">' + PHONE + "</a><br>",
    '<a href="mailto:' + CONTACT_EMAIL + '" style="color:#5B2E59;text-decoration:none;">' + CONTACT_EMAIL + "</a>",
    "</p>",
    "</td></tr>",
    "</table></td></tr></table></body></html>"
  ].join("");
}

function isValidEmail(s) {
  if (!s || /\s/.test(s)) return false;
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(s);
}

function escapeText(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

async function safeText(resp) {
  try {
    return await resp.text();
  } catch (e) {
    return "(no detail)";
  }
}
