# Stock Images Hosting -- Implementation Plan

Implements the spec in `docs/stock_images_spec.md`.


## Prerequisites

- [DONE] Run the full test suite to establish a green baseline.


## Steps

### Step 1 -- [DONE] Add `get_default_images_dir()` to `app/config.py`

### Step 2 -- [DONE] Add `--images-dir` CLI flag to `app/main_web.py`

### Step 3 -- [DONE] Add image-serving logic to `GofrDocWebServer`

### Step 4 -- [DONE] Add `GOFR_DOC_IMAGES_DIR` env var to Docker compose (prod)

### Step 5 -- [DONE] Add `GOFR_DOC_IMAGES_DIR` env var to Docker compose (dev/test)

### Step 6 -- [DONE] Create local `images/` directory

### Step 7 -- [DONE] Write unit tests (15 tests in `test/web/test_images.py`)

### Step 8 -- [DONE] Run targeted tests (15 passed)

### Step 9 -- [DONE] Run full test suite (596 passed, 0 failed)

### Step 10 -- [DONE] Update documentation (Stock Images section in features.md)


## Files changed / created

| File | Action |
|------|--------|
| `app/config.py` | Add `get_default_images_dir()` |
| `app/main_web.py` | Add `--images-dir` CLI flag, pass to server |
| `app/web_server/web_server.py` | Add `images_dir` param, listing + serving routes |
| `docker/compose.prod.yml` | Add env var, volume mount, volume declaration |
| `docker/compose.dev.yml` | Add env var, volume mount, volume declaration |
| `images/.gitkeep` | New -- empty placeholder |
| `.gitignore` | Add `images/*` exclusion |
| `test/web/test_images.py` | New -- unit tests |
| `docs/features.md` | Add Stock Images section |
