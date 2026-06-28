/* Eternal Life Hospice — AI assistant (Netlify Function).
 *
 * Calm, supportive, tightly guard-railed. It answers general questions about
 * Eternal Life Hospice and hospice care, never gives medical advice, and always
 * points people to a real person on the 24/7 line for anything urgent or personal.
 *
 * Required: set ANTHROPIC_API_KEY in your Netlify site settings
 *   (Site settings -> Environment variables). The key is read only on the
 *   server and is never sent to the browser. If the key is missing, this
 *   function returns a graceful message and the website falls back to the
 *   guided answers + phone number.
 *
 * Optional: ANTHROPIC_MODEL (defaults to claude-3-5-sonnet-latest).
 */

const PHONE = "805.953.7273";

const SYSTEM_PROMPT = `You are the gentle assistant for Eternal Life Hospice, Inc., on their website. You help families, patients, caregivers, referring providers, and prospective team members with general questions.

TONE — this is the most important rule:
- Warm, calm, unhurried, and deeply compassionate. Many visitors are frightened, grieving, or exhausted. Meet them with steadiness and kindness.
- Plain, simple language. Short replies — usually 2 to 4 sentences, but let the moment decide; sometimes one gentle line is enough. No jargon, no bullet lists unless truly helpful.
- Never sound salesy or clinical. Sound like a kind person who has time for them.
- Sound human, not scripted: use natural contractions (you're, we're, I'm, it's), and vary how you open each reply — never reuse the same opening or sentence twice in a conversation. Avoid stock filler like "I'm here to help you" or "Great question."
- Don't repeat the phone number in every message. Offer it when it genuinely helps (urgent, personal, or when they're ready to talk to someone) — not out of reflex.
- Before giving information, briefly acknowledge what the person is feeling. A short, genuine "That sounds really hard" or "I'm so glad you reached out" matters more than the facts that follow.
- Brand voice you may gently echo: "Care that honors life" and "here in the moments that matter most." Use sparingly and only when it feels natural.

WHAT YOU KNOW (only use these facts; do not invent specifics like prices, names, or dates):
- Eternal Life Hospice is an independent, Medicare-certified, CDPH-licensed, ACHC-accredited hospice agency.
- Serves Ventura County and Los Angeles County, California. Office: 4165 E Thousand Oaks Blvd, Suite 325B, Westlake Village, CA 91362.
- Phone (24/7 on-call nursing): ${PHONE}. Email: info@eternallifehospice.com.
- Same-day admissions are often possible.
- Hospice is covered under Medicare Part A, typically with no deductibles or copays for hospice services; also works with Medi-Cal and most plans.
- Care is provided wherever home is: private residence, assisted living, skilled nursing, and board-and-care.
- Integrative therapies, included at no additional cost: music therapy, therapeutic massage, reiki, aromatherapy, pet therapy, audiology support, holistic medicine, sound bath, and end-of-life doula support — alongside the clinical team.
- They welcome careers (nurses, aides, social workers, chaplains, bereavement counselors, integrative therapists, outreach, office staff) and volunteers.
- Founder & administrator: Aleksandra Dubina, a credentialed ACHC Certified Consultant with more than two decades in healthcare — eleven of those years in hospice. She founded Eternal Life Hospice out of personal experience with hospice care for a loved one, and leads a hands-on team that knows patients by name. If asked who founded or runs the agency, share this warmly and briefly. Do not volunteer private medical details about her or her family; if pressed, gently keep it general and offer the phone line.

HARD GUARDRAILS:
- You are NOT a medical professional. Never give medical advice, diagnoses, medication or dosing guidance, symptom interpretation, or clinical instructions. If asked anything clinical or about a specific person's symptoms or care, gently say a nurse can help and encourage calling ${PHONE} (available 24/7). For emergencies, tell them to call 911.
- Do not ask for or repeat sensitive personal or health details. If someone shares them, do not echo them back; kindly guide them to call so a real person can help safely.
- Stay on topics about Eternal Life Hospice, hospice/palliative care in general, and using this website. If asked something unrelated, kindly steer back and offer the phone number.
- For specifics you don't know (exact costs, a particular patient's eligibility, billing details, staff availability), don't guess — say a team member can help and offer ${PHONE}.
- Whenever it would help, make it easy to reach a person by mentioning the phone number ${PHONE}.

Always leave the person feeling cared for and never alone.`;

exports.handler = async function (event) {
  if (event.httpMethod !== "POST") {
    return json(405, { error: "Method not allowed" });
  }

  const hasAnthropic = !!process.env.ANTHROPIC_API_KEY;
  const hasOpenAI = !!process.env.OPENAI_API_KEY;
  if (!hasAnthropic && !hasOpenAI) {
    // Not configured yet — tell the site to fall back to guided answers + phone.
    return json(200, {
      reply: "",
      configured: false,
      fallback:
        "I'm not fully set up yet, but our team is always here for you. Please call " +
        PHONE +
        " any time and a real person will help."
    });
  }

  let body;
  try {
    body = JSON.parse(event.body || "{}");
  } catch (e) {
    return json(400, { error: "Invalid request" });
  }

  const incoming = Array.isArray(body.messages) ? body.messages : [];
  const cleaned = incoming
    .filter(function (m) {
      return m && (m.role === "user" || m.role === "assistant") && typeof m.content === "string";
    })
    .slice(-12)
    .map(function (m) {
      return { role: m.role, content: m.content.slice(0, 1500) };
    });

  if (cleaned.length === 0) {
    return json(400, { error: "No message provided" });
  }

  // Hard guardrails enforced in code (defense in depth — also protects direct
  // calls to this endpoint). Emergencies and clinical/health-detail questions
  // are never sent to the AI; we route the person to a real person instead.
  const lastUser = cleaned.filter(function (m) { return m.role === "user"; }).pop();
  const lastText = lastUser ? lastUser.content : "";
  const EMERGENCY = /(emergenc|call 911|\b911\b|can'?t breathe|cannot breathe|chest pain|suicid|kill myself|end my life|overdose|unconscious|not breathing|severe bleeding)/i;
  const CLINICAL = /\b(should (i|we|he|she|they|my)|is it (normal|safe|ok|okay)|how (much|many|often)|what dose|dosage|\d+\s?mg|increase (the|his|her)|lower (the|his|her)|stop (taking|the|giving)|side ?effect|morphine|oxycodone|hydrocodone|fentanyl|lorazepam|ativan|haldol|haloperidol|methadone|opioid|medication|prescrib|symptom|shortness of breath|short of breath|trouble breathing|in pain|severe pain|won'?t eat|not eating|not drinking|stopped eating|vomit|nause|fever|seizure|hallucinat|agitat|infection|\bwound\b|rash|swelling)\b/i;

  if (EMERGENCY.test(lastText)) {
    return json(200, {
      reply:
        "If this is a medical emergency, please call 911 right away. For an urgent hospice need, our nurses are available around the clock at " +
        PHONE +
        " \u2014 please call and a real person will help you right now.",
      guarded: true
    });
  }
  if (CLINICAL.test(lastText)) {
    return json(200, {
      reply:
        "I want to make sure you get the right help \u2014 a question like that is best for one of our nurses rather than me. Please call " +
        PHONE +
        " any time, day or night, and a caring person will talk it through with you. If this is an emergency, please call 911.",
      guarded: true
    });
  }

  // Generate a reply. Prefer Claude (warmer, more personable); if it isn't
  // configured or errors out, automatically fall back to OpenAI. Both calls use
  // the SAME warm, compassionate SYSTEM_PROMPT and the same settings, so the
  // tone is identical no matter which one answers.
  let reply = "";
  let lastErr = null;

  if (hasAnthropic) {
    try {
      reply = await callClaude(cleaned);
    } catch (err) {
      lastErr = err;
      console.error("Anthropic failed, falling back to OpenAI:", err && err.message);
    }
  }

  if (!reply && hasOpenAI) {
    try {
      reply = await callOpenAI(cleaned);
    } catch (err) {
      lastErr = err;
      console.error("OpenAI failed:", err && err.message);
    }
  }

  if (reply) {
    return json(200, { reply: reply, configured: true });
  }

  if (lastErr) {
    return json(502, {
      reply: "",
      fallback:
        "I'm having trouble responding right now. Please call us at " +
        PHONE +
        " \u2014 a real person will be glad to help."
    });
  }

  // Configured, but the model returned nothing usable.
  return json(200, {
    reply: "I'm not certain about that one, but our team can help \u2014 please call " + PHONE + ".",
    configured: true
  });
};

// Claude (Anthropic) — primary. Warm and personable. Returns reply text or throws.
async function callClaude(messages) {
  const model = process.env.ANTHROPIC_MODEL || "claude-3-5-sonnet-latest";
  const resp = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": process.env.ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01"
    },
    body: JSON.stringify({
      model: model,
      system: SYSTEM_PROMPT,
      temperature: 0.8,
      max_tokens: 320,
      messages: messages
    })
  });
  if (!resp.ok) {
    const detail = await resp.text();
    throw new Error("Anthropic " + resp.status + ": " + detail.slice(0, 300));
  }
  const data = await resp.json();
  return data && Array.isArray(data.content) && data.content[0] && data.content[0].text
    ? data.content[0].text.trim()
    : "";
}

// OpenAI — automatic fallback. Uses the same warm SYSTEM_PROMPT and settings,
// and defaults to the fuller gpt-4o (not the mini) so the tone stays human.
async function callOpenAI(messages) {
  const model = process.env.OPENAI_MODEL || "gpt-4o";
  const resp = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer " + process.env.OPENAI_API_KEY
    },
    body: JSON.stringify({
      model: model,
      temperature: 0.8,
      presence_penalty: 0.3,
      frequency_penalty: 0.3,
      max_tokens: 320,
      messages: [{ role: "system", content: SYSTEM_PROMPT }].concat(messages)
    })
  });
  if (!resp.ok) {
    const detail = await resp.text();
    throw new Error("OpenAI " + resp.status + ": " + detail.slice(0, 300));
  }
  const data = await resp.json();
  return data && data.choices && data.choices[0] && data.choices[0].message
    ? (data.choices[0].message.content || "").trim()
    : "";
}

function json(statusCode, obj) {
  return {
    statusCode: statusCode,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(obj)
  };
}
