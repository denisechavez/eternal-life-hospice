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
 * safely. Eligible forms: elh-family, elh-casemanager, elh-careers,
 * elh-care-brief-signup, elh-voice (collect an email), and elh-physician (the
 * /refer page now REQUIRES a work email — the partner always gets a PHI-free
 * referral confirmation; the homepage physician form has no email field and is
 * unaffected). Never auto-replied to: elh-coordinator and
 * elh-chat-callback (the chat already confirms on-screen).
 *
 * elh-chat-callback instead triggers an internal team notification to
 * referral@eternallifehospice.com with the callback details, so callback
 * requests reach the referral inbox even without Netlify UI notifications.
 */

const PHONE = "805.953.7273";
const SITE = "https://eternallifehospice.com";
const CONTACT_EMAIL = "info@eternallifehospice.com";
const CALLBACK_TEAM_EMAIL = "referral@eternallifehospice.com";
const FROM =
  process.env.AUTOREPLY_FROM ||
  "Eternal Life Hospice <" + CONTACT_EMAIL + ">";

// Forms eligible for an auto-reply. A reply is only ever sent when the submission
// also carries a valid email, so a form is safe to list here even when its email
// field is optional:
//   elh-family, elh-casemanager, elh-careers, elh-care-brief-signup,
//     elh-voice — collect an email directly.
//   elh-physician — the /refer page now REQUIRES a work email, so the partner
//     always gets a PHI-free referral confirmation. The homepage physician form
//     has no email field, so it is never affected.
//   elh-chat-callback — listed only so the handler runs its referral-inbox
//     notification; it returns before the auto-reply (chat confirms on-screen).
// Never auto-replied to: elh-coordinator, elh-chat-callback.
const ALLOWED_FORMS = [
  "elh-family",
  "elh-casemanager",
  "elh-careers",
  "elh-physician",
  "elh-chat-callback",
  "elh-care-brief-signup",
  "elh-voice"
];

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

    // Chat callback requests: notify the referral inbox, then stop — the chat
    // widget already confirms on the spot, so no auto-reply email is sent.
    // A notification failure is logged but never blocks the submission.
    if (formName === "elh-chat-callback") {
      try {
        await sendCallbackNotification(apiKey, data);
      } catch (e) {
        console.error(
          "Callback team notification failed: " + (e && e.message ? e.message : e)
        );
      }
      return { statusCode: 200, body: "callback notification handled; no auto-reply" };
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
    const isSignup = formName === "elh-care-brief-signup";
    const isVoice = formName === "elh-voice";
    // Referral confirmations: physician (/refer page) AND the homepage
    // case-manager discharge form — both are professional referrals, so both
    // get the same PHI-free "we received your referral" copy.
    const isReferral =
      formName === "elh-physician" || formName === "elh-casemanager";

    const subject = isVoice
      ? "Thank you for raising your hand — The Eternal Care Brief"
      : isSignup
      ? "You're on the list — The Eternal Care Brief"
      : isCareers
      ? "Thank you for your interest — Eternal Life Hospice"
      : isReferral
      ? "We received your referral — Eternal Life Hospice"
      : "We received your message — Eternal Life Hospice";

    // Static, PHI-free copy. We never echo the submitted clinical description.
    const lead = isVoice
      ? "Thank you for offering your voice. The Eternal Care Brief is built on the experience of professionals like you, and we're grateful you raised your hand. A member of our team will reach out shortly to talk about being featured, scheduling an educational session, or simply finding a good time to connect."
      : isSignup
      ? "Thank you for signing up for The Eternal Care Brief. You're on the list — each new issue brings clinical guidance for care professionals and plain-language support for families, published every other month. You can unsubscribe at any time by replying to any issue."
      : isCareers
      ? "Thank you for your interest in joining the Eternal Life Hospice team. We've received your application and a member of our team will review it and be in touch."
      : isReferral
      ? "Thank you for referring a patient to Eternal Life Hospice. We've received your referral, and our clinical intake team will reach out shortly to complete the details with you securely by phone. No patient information is ever exchanged by email."
      : "Thank you for reaching out to Eternal Life Hospice. We've received your message, and a member of our team will be in touch with you shortly.";

    const text = isSignup
      ? [
          greeting,
          "",
          lead,
          "",
          "Read the latest issue: " + SITE + "/care-brief/hospice-is-part-of-life-a-continuation-of-care",
          "Explore the Care Brief library: " + SITE + "/care-brief",
          "",
          "Download the Family Guide (free PDF): " + SITE + "/ELH_Family_Guide.pdf",
          "",
          "Know a colleague or a family who would find this helpful? Forward this email, or share the Care Brief: " + SITE + "/care-brief",
          "",
          "We're here for you — call us anytime at " + PHONE + ".",
          "",
          "With care,",
          "Eternal Life Hospice",
          PHONE,
          CONTACT_EMAIL
        ].join("\n")
      : [
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

    const html = isSignup ? renderSignupHtml(greeting, lead) : renderHtml(greeting, lead);

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

/**
 * Internal notification for chat callback requests → referral inbox.
 * The requester's own details (name, phone, preferred time, note) are what the
 * team needs to make the call, so they are included — this email only goes to
 * the internal referral inbox, never to an outside address.
 */
async function sendCallbackNotification(apiKey, data) {
  const name = String(data.name || "").trim() || "(no name given)";
  const phone = String(data.phone || "").trim() || "(no phone given)";
  const email = String(data.email || "").trim() || "(none)";
  const time = String(data.preferred_time || "").trim() || "(no preference)";
  const note = String(data.message || "").trim() || "(none)";

  const text = [
    "New callback request from the website chat.",
    "",
    "Name: " + name,
    "Phone: " + phone,
    "Email: " + email,
    "Best time to call: " + time,
    "Note: " + note,
    "",
    "Please call them back as soon as possible."
  ].join("\n");

  const rows = [
    ["Name", escapeText(name)],
    ["Phone", escapeText(phone)],
    ["Email", escapeText(email)],
    ["Best time to call", escapeText(time)],
    ["Note", escapeText(note)]
  ]
    .map(function (r) {
      return (
        '<tr><td style="padding:6px 14px 6px 0;color:#6b5f57;font-size:14px;white-space:nowrap;vertical-align:top;">' +
        r[0] +
        '</td><td style="padding:6px 0;color:#3C1C3B;font-size:15px;">' +
        r[1] +
        "</td></tr>"
      );
    })
    .join("");

  const html = [
    '<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;padding:0;background:#F5F0EB;">',
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F5F0EB;padding:32px 0;">',
    '<tr><td align="center">',
    '<table role="presentation" width="520" cellpadding="0" cellspacing="0" style="max-width:520px;width:100%;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #D8CDBF;">',
    '<tr><td style="background:#5B2E59;padding:22px 32px;">',
    '<div style="font-family:Georgia,\'Times New Roman\',serif;color:#F5F0EB;font-size:20px;letter-spacing:.3px;">New callback request — website chat</div>',
    "</td></tr>",
    '<tr><td style="padding:26px 32px;font-family:Georgia,\'Times New Roman\',serif;">',
    '<table role="presentation" cellpadding="0" cellspacing="0">' + rows + "</table>",
    '<div style="height:1px;background:#EDE6DE;margin:20px 0;"></div>',
    '<p style="margin:0;color:#6b5f57;font-size:13px;line-height:1.6;">Submitted through the chat widget on eternallifehospice.com. Please call them back as soon as possible.</p>',
    "</td></tr>",
    "</table></td></tr></table></body></html>"
  ].join("");

  const resp = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: "Bearer " + apiKey,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      from: FROM,
      to: [CALLBACK_TEAM_EMAIL],
      reply_to: CONTACT_EMAIL,
      subject: "Callback request — " + String(data.name || "website visitor").trim(),
      text: text,
      html: html
    })
  });

  if (!resp.ok) {
    const detail = await safeText(resp);
    throw new Error("Resend " + resp.status + ": " + detail);
  }
}

/**
 * Branded welcome email for The Eternal Care Brief signup — richer than the
 * generic confirmation: latest-issue + library buttons, a Family Guide
 * download, and a share-with-a-colleague block. All links point at the live
 * site; the Family Guide PDF and logo are confirmed live assets.
 */
function renderSignupHtml(greeting, lead) {
  const btn = function (href, label, solid) {
    return (
      '<a href="' + href + '" style="display:inline-block;background:' +
      (solid ? "#5B2E59" : "#ffffff") +
      ";color:" + (solid ? "#F5F0EB" : "#5B2E59") +
      ";border:1.5px solid #5B2E59;border-radius:999px;padding:11px 22px;font-family:Georgia,'Times New Roman',serif;font-size:15px;text-decoration:none;\">" +
      label + "</a>"
    );
  };
  const shareMailto =
    "mailto:?subject=" +
    encodeURIComponent("Worth a read — The Eternal Care Brief") +
    "&body=" +
    encodeURIComponent(
      "I thought of you when I read this. The Eternal Care Brief shares clinical guidance for care professionals and plain-language support for families, from Eternal Life Hospice:\n\n" +
        SITE + "/care-brief\n\nYou can sign up there to receive each new issue."
    );
  return [
    '<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;padding:0;background:#F5F0EB;">',
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F5F0EB;padding:32px 0;">',
    '<tr><td align="center">',
    '<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #D8CDBF;">',
    // Header
    '<tr><td align="center" style="background:#3C1C3B;padding:34px 32px 30px;">',
    '<img src="' + SITE + '/assets/logo-cream.png" alt="Eternal Life Hospice" width="170" style="display:block;margin:0 auto 18px;max-width:170px;height:auto;">',
    '<div style="font-family:Georgia,\'Times New Roman\',serif;color:#F5F0EB;font-size:24px;letter-spacing:.3px;">Welcome to <span style="color:#C9B07E;">The Eternal Care Brief</span></div>',
    "</td></tr>",
    // Body
    '<tr><td style="padding:32px 36px 8px;font-family:Georgia,\'Times New Roman\',serif;color:#3C1C3B;font-size:16px;line-height:1.7;">',
    '<p style="margin:0 0 14px;">' + greeting + "</p>",
    '<p style="margin:0 0 22px;">' + lead + "</p>",
    '<table role="presentation" align="center" cellpadding="0" cellspacing="0" style="margin:0 auto 10px;"><tr>',
    '<td style="padding:0 6px 12px;">' + btn(SITE + "/care-brief/hospice-is-part-of-life-a-continuation-of-care", "Read the Latest Issue &#8594;", true) + "</td>",
    '<td style="padding:0 6px 12px;">' + btn(SITE + "/care-brief", "Explore the Library", false) + "</td>",
    "</tr></table>",
    "</td></tr>",
    // Family Guide block
    '<tr><td style="padding:10px 36px;">',
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F5F0EB;border:1px solid #E4DACB;border-radius:12px;"><tr>',
    '<td style="padding:22px 26px;font-family:Georgia,\'Times New Roman\',serif;">',
    '<div style="color:#3C1C3B;font-size:17px;margin:0 0 6px;">A gift for the families you serve</div>',
    '<p style="margin:0 0 14px;color:#6b5f57;font-size:14px;line-height:1.65;">Our Family Guide walks families through hospice in plain language — what to expect, who visits, and how to prepare. Keep a copy, or pass it along.</p>',
    btn(SITE + "/ELH_Family_Guide.pdf", "Download the Family Guide", true),
    "</td></tr></table>",
    "</td></tr>",
    // Share block
    '<tr><td align="center" style="padding:22px 36px 6px;font-family:Georgia,\'Times New Roman\',serif;">',
    '<div style="height:1px;background:#EDE6DE;margin:0 0 22px;"></div>',
    '<p style="margin:0 0 12px;color:#3C1C3B;font-size:15px;line-height:1.6;">Know a colleague or a family who would find this helpful?</p>',
    btn(shareMailto, "Share the Care Brief &#8594;", false),
    "</td></tr>",
    // Here for you footer
    '<tr><td align="center" style="background:#5B2E59;padding:26px 32px;margin-top:24px;">',
    '<div style="font-family:Georgia,\'Times New Roman\',serif;color:#F5F0EB;font-size:17px;margin:0 0 8px;">Here for You</div>',
    '<p style="margin:0;font-family:Georgia,\'Times New Roman\',serif;color:#E9DFEA;font-size:14px;line-height:1.7;">A nurse is reachable 24/7. Call <a href="tel:8059537273" style="color:#C9B07E;font-weight:bold;text-decoration:none;">' + PHONE + '</a> or email <a href="mailto:' + CONTACT_EMAIL + '" style="color:#C9B07E;text-decoration:none;">' + CONTACT_EMAIL + "</a>.</p>",
    "</td></tr>",
    '<tr><td align="center" style="padding:18px 32px;font-family:Georgia,\'Times New Roman\',serif;color:#9b8f85;font-size:12px;line-height:1.6;">Eternal Life Hospice &middot; 4165 E Thousand Oaks Blvd, Suite 325B, Westlake Village, CA 91362<br>Serving Ventura &amp; Los Angeles County &middot; Medicare-Certified &middot; CDPH-Licensed &middot; ACHC-Accredited<br>You can unsubscribe at any time by replying to any issue.</td></tr>',
    "</table></td></tr></table></body></html>"
  ].join("");
}

function renderHtml(greeting, lead) {
  return [
    '<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;padding:0;background:#F5F0EB;">',
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
