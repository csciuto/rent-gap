# Rent Burden: Renters 23–35

A one-page dashboard (`docs/index.html`, which loads `docs/data.json`) built from an IPUMS ACS extract by `build_parquet.py`
and `build_data.py`. See README.md for definitions.

Follows the app standards in [csciuto/app-template STANDARDS.md](https://github.com/csciuto/app-template/blob/main/STANDARDS.md).
Commit and push freely once tests pass.

## This app

- `.github/workflows/deploy.yml` runs `test_pipeline.py` (tests needing the raw extract or `renters.parquet` skip
  when those aren't present, as in CI) and the browser tests (desktop and phone, axe), then publishes `docs/` at
  https://corey.sciu.to/rent-gap/ with a version stamp. `/rent-gap/docs/` redirects there.
- Locally the browser tests serve the repo root, so the page is at `/docs/`.
- Series colors: `COLORS` for chart lines, `TEXT_COLORS` (same hues, darkened to 4.5:1) wherever a series color
  is used for text. Switched-off series rows are faded on purpose and skipped by the contrast check.
