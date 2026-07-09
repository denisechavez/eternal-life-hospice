const OpenAI = require("openai");

// Uses Replit AI Integrations (OpenAI-compatible gateway). No personal API key
// needed; AI_INTEGRATIONS_OPENAI_BASE_URL and AI_INTEGRATIONS_OPENAI_API_KEY
// are provided automatically once the OpenAI integration is enabled.
function getClient() {
  return new OpenAI({
    apiKey: process.env.AI_INTEGRATIONS_OPENAI_API_KEY,
    baseURL: process.env.AI_INTEGRATIONS_OPENAI_BASE_URL,
  });
}

const FIELDS = [
  "company",
  "contact_name",
  "contact_title",
  "contact_email",
  "contact_phone",
  "address",
  "city",
];

async function extractCardContact(dataUrl) {
  const client = getClient();
  const resp = await client.chat.completions.create({
    model: "gpt-5.4-mini",
    messages: [
      {
        role: "system",
        content:
          "You read business cards for a healthcare outreach team. Return only the requested JSON. Never invent data: if a field is not clearly printed on the card, use an empty string.",
      },
      {
        role: "user",
        content: [
          {
            type: "text",
            text:
              'Extract the contact details from this business card. Respond with a JSON object using exactly these keys: company, contact_name, contact_title, contact_email, contact_phone, address, city. "address" is the street address only (no city, state, or zip). "city" is the city name only. Use "" for anything not present.',
          },
          { type: "image_url", image_url: { url: dataUrl } },
        ],
      },
    ],
    response_format: { type: "json_object" },
  });

  let parsed = {};
  try {
    parsed = JSON.parse(resp.choices?.[0]?.message?.content || "{}");
  } catch (_) {
    parsed = {};
  }

  const out = {};
  for (const k of FIELDS) out[k] = String(parsed[k] || "").trim();
  return out;
}

module.exports = { extractCardContact };
