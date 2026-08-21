# Marketplace mock icons (Docker seed source)

Same placeholders as `frontend/public/marketplace-mocks/`. Edit here when seeding from the app container.

## Raster size (PNG / JPEG / WebP)

Icons are shown as **circles**. Export a **square 1:1** file.

- **Target: 512×512 px** — sharp on 3× displays, typically well under the 512 KB upload cap.
- Minimum: 256×256 px (same as in-app crop output).
- Keep the subject in the center ~90%; corners are clipped.
- PNG for transparency, JPEG/WebP for photos. Hard limit **512 KB**.
