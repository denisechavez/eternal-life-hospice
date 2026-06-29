---
name: Canvas image-shape ops
description: How to put a local image on the canvas and refresh it — upload path, port, and create-vs-update payload quirks.
---

# Putting a local image on the canvas (image shapes)

Canvas image shapes will NOT load an arbitrary app URL. Two hard requirements:

1. **Asset must live under `.canvas/assets/`** and be served on the canvas asset
   port **5904** (not the app's 5000). URL form:
   `https://<dev-domain>:5904/<file>.jpg`. The plain app-domain URL (443) fails
   with "Image assets must be uploaded to the canvas before they can be used".
   Workflow: `cp <img> .canvas/assets/<name>.jpg` then use the :5904 URL.

2. **CREATE vs UPDATE payloads differ** (the error messages are explicit if you
   get it wrong):
   - CREATE: `{type:"create", shapeId, shape:{type:"image", x,y,w,h, src, altText}}`
   - UPDATE: `{type:"update", shapeId, updates:{shapeType:"image", src}}`
     — `updates` (not `shape`), and `shapeType` is REQUIRED inside `updates`.

3. **Cache-bust quirk:** appending `?v=<ts>` to `src` is REQUIRED on UPDATE to
   force the board to re-fetch a same-name file, but on CREATE the `?query`
   breaks mime sniffing ("Expected string, got a boolean" for mimeType). So:
   create with a clean `.jpg` URL, update with `?v=` appended.

After create/update, call `focusCanvasShapes({shapeIds, animateMs, padding})` to
bring shapes into view (the user must have asked to "see" it). `presentArtifact`
does NOT work for plain image shapes — it only knows iframe artifacts and errors
with "Artifact '<id>' not found. Available artifacts: []".
