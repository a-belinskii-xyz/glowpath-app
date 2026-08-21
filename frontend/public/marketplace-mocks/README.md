# Marketplace mock icons

Temporary placeholder SVGs for the icon catalog. Replace files **in both places** (same filenames), or only in `backend/app/data/marketplace_mocks/` if you seed from Docker:

- `frontend/public/marketplace-mocks/` — preview in the browser (`/marketplace-mocks/fox-happy.svg`)
- `backend/app/data/marketplace_mocks/` — used by seed inside Docker

| File | Suggested vibe |
|------|----------------|
| `fox-happy.svg` | joy / animals |
| `fox-sad.svg` | sadness / animals |
| `fox-dumbbell.svg` | sport / fitness |
| `fox-sleep.svg` | night / calm |
| `blob-joy.svg` | joy / energy |
| `star-burst.svg` | energy / joy |
| `rain-cloud.svg` | sadness / weather |
| `coffee-cup.svg` | calm / energy |

## Raster size (PNG / JPEG / WebP)

Icons are shown as **circles** (list ~20px, picker ~38px, market ~88px CSS). Export a **square 1:1** file.

| | Recommendation |
|---|---|
| **Target** | **512×512 px** |
| Minimum | 256×256 px (same as in-app crop output; soft on 3× displays) |
| Avoid | 1024×1024+ — extra pixels are unused and PNG often exceeds the upload cap |
| File size | **≤ 512 KB** (hard limit) |
| Format | PNG if you need transparency; JPEG/WebP for photos |
| Safe area | Keep the subject in the center ~90% — corners are clipped by the circle |

512×512 is enough for 3× retina on the largest marketplace thumb (~88×3 ≈ 264 px) and stays small on disk.

After replacing art, re-seed:

```bash
docker compose exec app python -m app.services.marketplace_seed
```
