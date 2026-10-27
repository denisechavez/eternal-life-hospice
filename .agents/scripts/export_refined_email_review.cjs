// Export the canvas letter renderer without modifying or activating live templates.
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { createRequire } = require("node:module");
const localRequire = createRequire(path.resolve("artifacts/review-design-sandbox/package.json"));
const ts = localRequire("typescript");
const source = fs.readFileSync("artifacts/review-design-sandbox/src/components/mockups/elh-email-review/RefinedLetter.tsx", "utf8");
const renderer = source.slice(source.indexOf("function escapeHtml"), source.indexOf("export function RefinedLetter"));
const logo = "data:image/png;base64," + fs.readFileSync("artifacts/review-design-sandbox/public/email-design/logo-cream.png").toString("base64");
const context = { LOGO_URL: logo };
vm.createContext(context);
vm.runInContext(ts.transpileModule(renderer, { compilerOptions: { target: ts.ScriptTarget.ES2021 } }).outputText, context);
const messages = JSON.parse(fs.readFileSync("artifacts/review-design-sandbox/public/email-design/approved-messages.json", "utf8"));
if (messages.length !== 14) throw new Error("Expected all 14 review messages.");
const names = {
  family: "Family care request", physician: "Physician referral",
  "case-manager": "Case manager referral", coordinator: "Care coordinator request",
  callback: "Callback request", career: "Career inquiry",
  subscriber: "Care Brief subscription", "share-voice": "Share your voice",
  "speaking-engagement": "Speaking engagement", "education-session": "Education session",
  "general-meeting": "General meeting request", "be-featured": "Be featured",
  "all-interests": "All interests", "aleksandra-meeting": "Meeting with Aleksandra"
};
const esc = context.escapeHtml;
const contents = messages.map((m, i) => `<li><span>${esc(names[m.key])}</span><span>${i + 2}</span></li>`).join("");
const pages = messages.map((message, index) => {
  const document = context.makeEmailDocument(message);
  const body = document.match(/<body[^>]*>([\s\S]*)<\/body>/)[1];
  return `<section class="sheet">
    <header><span>${String(index + 1).padStart(2, "0")} · ${esc(names[message.key])}</span><span>For review only · Not live</span></header>
    <p class="subject"><b>Subject:</b> ${esc(message.subject)}</p>
    <div class="letter">${body}</div>
    <footer>Eternal Life Hospice · Acknowledgment email review <span>${index + 2} / 15</span></footer>
  </section>`;
}).join("");
const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Eternal Life Hospice — Acknowledgment Email Review</title>
<style>
@page{size:letter;margin:0}
*{box-sizing:border-box}
body{margin:0;color:#414141;background:#fff;font-family:Arial,sans-serif}
.sheet{width:8.5in;height:11in;padding:.35in .5in .4in;position:relative;break-after:page;page-break-after:always}
.sheet:last-child{break-after:auto;page-break-after:auto}
header{display:flex;justify-content:space-between;gap:10px;border-bottom:1px solid #d8d4cb;padding-bottom:10px;font-size:10px;color:#555}
.subject{font:12px/1.5 Arial,sans-serif;margin:14px 0 8px}
.letter{zoom:.78}
.letter>table>tbody>tr>td{padding:12px 0 0!important}
footer{position:absolute;bottom:.28in;left:.5in;right:.5in;border-top:1px solid #dedbd3;padding-top:8px;font-size:9px;color:#666;display:flex;justify-content:space-between}
.cover{padding-top:.8in}
.cover .brand{background:#432440;padding:25px;margin-bottom:30px}
.cover .brand img{width:142px}
h1{font:36px/1.15 Georgia,serif;margin:0 0 16px;color:#414141}
.intro{font:15px/1.65 Georgia,serif}
.status{background:#f5f2eb;border-left:3px solid #b5a279;padding:14px 18px;font:13px/1.6 Arial,sans-serif;margin:22px 0}
ol{list-style:none;padding:0;margin:24px 0 0}
li{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #e9e5dd;font-size:12px}
</style></head><body>
<section class="sheet cover">
<div class="brand"><img src="${logo}" alt="Eternal Life Hospice"></div>
<h1>Acknowledgment emails<br>Review packet</h1>
<p class="intro">Prepared for Aleksandra’s review and approval.<br>All 14 messages in the refined dark grey letter layout.</p>
<div class="status"><b>For review only — not live.</b><br>This packet does not send emails or change the website. Names and confirmation numbers are placeholders. Please identify any requested changes by message title or page number.</div>
<ol>${contents}</ol>
<footer>Eternal Life Hospice · Acknowledgment email review <span>1 / 15</span></footer>
</section>${pages}</body></html>`;
const out = "generated-artifacts/email-review";
fs.mkdirSync(out, { recursive: true });
fs.writeFileSync(path.join(out, "ELH-Refined-Acknowledgment-Emails-Review.html"), html);
console.log(`Exported ${messages.length} messages using the exact canvas renderer.`);
