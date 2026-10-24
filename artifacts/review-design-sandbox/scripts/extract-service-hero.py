"""Snapshot the real Services hero and its styles for isolated canvas studies."""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = ROOT / "artifacts/review-design-sandbox"
GROUP = ARTIFACT / "src/components/mockups/elh-service-photo-options/_shared"
PUBLIC = ARTIFACT / "public/images/elh-service-photo-options"
GROUP.mkdir(parents=True, exist_ok=True)
PUBLIC.mkdir(parents=True, exist_ok=True)
source = (ROOT / "website/previews/services-directory.html").read_text()
hero = re.search(r'<section class="cc-hero">.*?</section>', source, re.S)[0]
prefix = "/__reviews-mockup/images/elh-service-photo-options/"
hero = hero.replace("/__service-preview-assets/hero.webp", prefix + "hero.webp")
(GROUP / "source.json").write_text(json.dumps({
    "source": "website/previews/services-directory.html",
    "hero": '<div id="service-page" class="services-directory-page">' + hero + "</div>",
}, indent=2) + "\n")
shutil.copyfile(ROOT / "website/previews/service-pages.css", GROUP / "source.css")
shutil.copyfile(ROOT / "generated-artifacts/service-community-preview/hero.webp",
                PUBLIC / "hero.webp")
base = (ROOT / "website/elh-preview/assets/elh.css").read_text()
faces = re.findall(r"@font-face\s*\{[^}]+\}", base)
font_css = []
for face in faces:
    names = re.findall(r"[\w-]+\.woff2", face)
    if not names:
        continue
    name = names[0]
    original = ROOT / "website/elh-preview/assets/fonts" / name
    if not original.is_file():
        raise FileNotFoundError(original)
    shutil.copyfile(original, PUBLIC / name)
    face = re.sub(r"url\([^)]*\.woff2[^)]*\)",
                  "url('" + prefix + name + "')", face)
    font_css.append(face)
(GROUP / "fonts.css").write_text("\n".join(font_css) + "\n")
print("Extracted actual hero markup, original CSS, photograph and", len(font_css), "font faces")
