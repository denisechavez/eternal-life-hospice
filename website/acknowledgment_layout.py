"""Approved Personal Correspondence email presentation; no routing or transport."""
import html
from pathlib import Path


def paragraph_row(paragraph):
    safe = html.escape(paragraph)
    if paragraph.startswith("Need to speak with someone now?\n"):
        question, availability, call = map(html.escape, paragraph.split("\n"))
        return f"""<tr><td style="padding:14px 0 24px">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;border-top:1px solid #c8b58d;border-bottom:1px solid #c8b58d">
        <tr><td style="padding:17px 0 16px">
          <p style="margin:0 0 5px;color:#424242;font:bold 16px/1.45 Georgia,'Times New Roman',serif">{question}</p>
          <p style="margin:0 0 13px;color:#555555;font:15px/1.55 Georgia,'Times New Roman',serif">{availability}</p>
          <a href="tel:18059537273" style="display:inline-block;color:#414141;background:#eee8dc;border:1px solid #d5c8ad;padding:10px 15px;font:bold 15px/1.25 Arial,sans-serif;text-decoration:none">{call}</a>
        </td></tr>
      </table>
    </td></tr>"""
    if paragraph.startswith("Confirmation number:"):
        return f"""<tr><td style="padding:14px 0 0">
      <p style="margin:0;color:#555555;font:13px/1.6 Arial,sans-serif;letter-spacing:.1px">{safe}</p>
    </td></tr>"""
    if paragraph.startswith((
        "To help protect patient privacy",
        "If you are experiencing a medical emergency",
        "Important: This confirms receipt",
    )):
        return f"""<tr><td style="padding:9px 0 0">
      <p style="margin:0;color:#555555;font:13px/1.65 Arial,sans-serif">{safe}</p>
    </td></tr>"""
    if paragraph.startswith(("Dear ", "Hello ")):
        style = "margin:0 0 23px;color:#4a4a4a;font:16px/1.65 Georgia,'Times New Roman',serif"
    elif paragraph in ("With care,", "With appreciation,", "Warm regards,", "Warmly,"):
        style = "margin:24px 0 3px;color:#4a4a4a;font:16px/1.65 Georgia,'Times New Roman',serif"
    elif paragraph.startswith("The Eternal Life Hospice"):
        style = "margin:0 0 4px;color:#414141;font:bold 16px/1.5 Georgia,'Times New Roman',serif"
    elif paragraph in ("Here in Moments That Matter Most.", "Care That Honors Life."):
        style = "margin:0 0 21px;color:#65605d;font:italic 14px/1.6 Georgia,'Times New Roman',serif"
    else:
        style = "margin:0 0 17px;color:#414141;font:16px/1.7 Georgia,'Times New Roman',serif"
    return f'<tr><td><p style="{style}">{safe}</p></td></tr>'


_TEMPLATE = (Path(__file__).resolve().parent / "email-templates/personal-correspondence.html").read_text(encoding="utf-8")


def render_document(paragraphs, contact_email):
    # Substitute once, so escaped user content cannot become a template token.
    before, after = _TEMPLATE.split("<!-- LETTER_ROWS -->")
    return (
        before + "".join(paragraph_row(p) for p in paragraphs)
        + after.replace("{{CONTACT_EMAIL}}", html.escape(contact_email, quote=True))
    )
