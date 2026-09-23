import batch1 from "../../../../../../website/content/30-day-journal/batch-1.json";
import batch2 from "../../../../../../website/content/30-day-journal/batch-2.json";
import batch3 from "../../../../../../website/content/30-day-journal/batch-3.json";
import batch4 from "../../../../../../website/content/30-day-journal/batch-4.json";
import batch5 from "../../../../../../website/content/30-day-journal/batch-5.json";
import campaign1 from "../../../../../../exports/email-campaigns/30-day-journal/campaign-1.html?raw";
import campaign2 from "../../../../../../exports/email-campaigns/30-day-journal/campaign-2.html?raw";
import campaign3 from "../../../../../../exports/email-campaigns/30-day-journal/campaign-3.html?raw";
import campaign4 from "../../../../../../exports/email-campaigns/30-day-journal/campaign-4.html?raw";
import approvedFamilyGuide from "../../../../../../exports/email/elh-family-guide-email-2.html?raw";
import approvedCareBrief from "../../../../../../exports/email/eternal-care-brief-introduction-email.html?raw";

export type JournalArticle = (typeof batch1)[number];
export type EmailCampaign = {
  html: string;
  subject: string;
  preheader: string;
  plainText: string;
  sendDate: string;
  framework: "approved" | "journal-draft";
};

export const journalArticles: JournalArticle[] = [
  ...[...batch1, ...batch2, ...batch3, ...batch4, ...batch5].filter(article => !("publicationStatus" in article) || article.publicationStatus !== "archived"),
];

const plainText = [
  `Knowing when to call\nA conversation can begin before a crisis.\n\nWondering whether it is time to ask about hospice? You do not have to wait for a crisis or have every answer ready.\n\nA conversation can begin when a serious illness is changing daily life: more time in bed, repeated hospital visits, increasing help with eating or bathing, or symptoms that are becoming harder to manage. These signs do not make an eligibility decision—but they are meaningful reasons to ask a clinician for an evaluation.\n\nHospice is generally considered when a physician certifies a life expectancy of six months or less if an illness follows its usual course. A hospice team can explain options and next steps without pressure.\n\nRead the guide: https://eternallifehospice.com/blog/knowing-when-to-call\n\nQuestions? Call 805.953.7273\nEternal Life Hospice | Care That Honors Life.\nEducational information only; not medical advice.\nUnsubscribe: {{ unsubscribe }}`,
  `Understanding coverage and care\nHospice, palliative care, and Medicare—clearly.\n\nMedicare, hospice, and palliative care can feel like a lot to sort through. Hospice is a Medicare benefit for people who meet eligibility requirements and choose comfort-focused care rather than treatment intended to cure a terminal illness. Palliative care focuses on comfort and quality of life at any stage of serious illness and can often accompany disease-directed treatment.\n\nThe hospice benefit is generally covered in full with no deductible for the benefit itself. Some comfort medications may have a small copayment, and inpatient respite can involve coinsurance. Ask your hospice and plan about your situation.\n\nUnderstand your options: https://eternallifehospice.com/blog/understanding-coverage-and-care\n\nQuestions? Call 805.953.7273\nEternal Life Hospice | Care That Honors Life.\nCoverage varies; confirm benefits with your plan and care team.\nUnsubscribe: {{ unsubscribe }}`,
  `Hospice close to home\nLocal support in the Conejo Valley and nearby communities.\n\nFamiliar places and trusted faces can make care feel more personal. Eternal Life Hospice serves families across Thousand Oaks, Simi Valley, Camarillo, the Conejo Valley, and Moorpark.\n\nOur team supports people wherever they call home—including a private residence, assisted living community, or skilled nursing setting, when appropriate. Learn how our local team coordinates comfort-focused care and family support.\n\nExplore local hospice care: https://eternallifehospice.com/blog/hospice-close-to-home\n\nQuestions? Call 805.953.7273\nEternal Life Hospice | Care That Honors Life.\nService availability depends on clinical need and location.\nUnsubscribe: {{ unsubscribe }}`,
  `What support really includes\nHospice is more than visits.\n\nDepending on an individual plan of care, support may include medically necessary equipment and supplies, help managing symptoms, and access to a nurse by phone 24/7. A social worker can help with practical and emotional needs, while a chaplain or counselor can offer spiritual or personal support.\n\nCaregivers may also be able to use short-term inpatient respite—up to five consecutive days when arranged and clinically appropriate. The interdisciplinary team reviews care and adjusts support as needs change.\n\nSee what support includes: https://eternallifehospice.com/blog/what-hospice-support-includes\n\nQuestions? Call 805.953.7273\nEternal Life Hospice | Care That Honors Life.\nServices vary by care plan and eligibility; speak with your clinician for guidance.\nUnsubscribe: {{ unsubscribe }}`,
];

export const emailCampaigns: EmailCampaign[] = [
  {
    html: approvedFamilyGuide,
    subject: "A Complimentary Family Guide for Patients and Caregivers",
    preheader: "A practical hospice resource created to support families and healthcare professionals.",
    plainText: "A complimentary family guide for patients and caregivers.\n\nA practical hospice resource created to support families and healthcare professionals.\n\nOpen the Family Guide: https://eternallifehospice.com/family-guide\n\nQuestions? Call 805.953.7273\nEternal Life Hospice | Care That Honors Life.\nUnsubscribe: {{ unsubscribe }}",
    sendDate: "Approved template",
    framework: "approved",
  },
  {
    html: approvedCareBrief,
    subject: "Introducing The Eternal Care Brief",
    preheader: "Issue One is here—hospice as a continuation of care.",
    plainText: "Introducing The Eternal Care Brief.\n\nIssue One reframes hospice as a continuation of care, not its end.\n\nRead Issue One: https://eternallifehospice.com/care-brief/hospice-is-part-of-life-a-continuation-of-care\n\nQuestions? Call 805.953.7273\nEternal Life Hospice | Care That Honors Life.\nUnsubscribe: {{ unsubscribe }}",
    sendDate: "Approved template",
    framework: "approved",
  },
  { html: campaign1, subject: "Knowing When to Call: A Gentle Starting Point", preheader: "A conversation can begin before a crisis. Learn which changes may be worth discussing with a clinician.", plainText: plainText[0], sendDate: "Sep 23, 2026", framework: "journal-draft" },
  { html: campaign2, subject: "Hospice, Palliative Care, and Medicare—Clearly", preheader: "A plain-language look at hospice, palliative care, and common Medicare coverage questions.", plainText: plainText[1], sendDate: "Sep 30, 2026", framework: "journal-draft" },
  { html: campaign3, subject: "Hospice Close to Home in the Conejo Valley", preheader: "Local, comfort-focused support for families in Thousand Oaks, Simi Valley, Camarillo, and nearby communities.", plainText: plainText[2], sendDate: "Oct 7, 2026", framework: "journal-draft" },
  { html: campaign4, subject: "What Hospice Support Really Includes", preheader: "Equipment, 24/7 nursing access, social work, and respite—see how a hospice team supports families.", plainText: plainText[3], sendDate: "Oct 14, 2026", framework: "journal-draft" },
];