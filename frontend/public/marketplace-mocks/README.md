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

After replacing art, re-seed:

```bash
docker compose exec app python -m app.services.marketplace_seed
```
