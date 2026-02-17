# Stock Images Hosting -- Specification

## Overview

Add the ability for gofr-doc's web server to host stock images from a Docker
volume mounted at `/images`.  Images are managed externally (placed into the
volume by operators or other tooling); the web server only serves them
read-only.  Document templates/fragments already know how to reference images
via URL -- this feature simply provides the hosting side.

## Scope

- Read-only image serving via the existing FastAPI web server.
- A JSON listing endpoint so callers can discover available images.
- Subdirectory structure inside `/images` is preserved in URL paths.
- No authentication required (images are considered public assets).
- No upload, update, or delete functionality (out of scope).

## Functional Requirements

### FR-1: Serve images at GET /images/{path}

Any file under `/images` in the container is reachable via the web server at
the path `/images/<relative-path>`.

Example: a file at `/images/logos/acme.png` is served at
`GET /images/logos/acme.png` with `Content-Type: image/png`.

Supported formats (by extension): `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`,
`.webp`, `.ico`, `.bmp`, `.tiff`.

Requests for non-image files or paths that escape the `/images` root via `..`
traversal must be rejected (400/404).

### FR-2: Listing endpoint at GET /images

Returns a JSON array of all image file paths (relative to `/images`) found
recursively in the volume.

Response shape:

```
{
  "status": "success",
  "data": {
    "images": [
      "logos/acme.png",
      "charts/q1-revenue.svg",
      "hero.jpg"
    ],
    "count": 3
  }
}
```

If the `/images` directory does not exist or is empty, returns an empty list
(not an error).

### FR-3: Docker volume mount

A new named volume `gofr-doc-images` is mounted at `/home/gofr-doc/images`
inside every container that runs the web server, in both `compose.prod.yml`
and `compose.dev.yml`.

The volume is `external: false` (Docker-managed, persistent).

### FR-4: No authentication

Image endpoints (`GET /images` and `GET /images/{path}`) do not require
`X-Auth-Token` or `Authorization` headers.  They behave like `/ping`.

### FR-5: Configurable images directory

The images directory path is configurable via:

- CLI flag: `--images-dir`
- Environment variable: `GOFR_DOC_IMAGES_DIR`
- Default: `/home/gofr-doc/images` (prod) / `<project-root>/images` (dev)

## Non-Functional Requirements

- Path traversal protection: reject any resolved path outside the images root.
- Reasonable `Content-Type` detection based on file extension.
- Logging via `StructuredLogger` for every image request (path, status,
  size_bytes, duration_ms).
- No in-memory caching -- serve directly from disk (the volume is local).
- Standard `Cache-Control` headers (e.g. `max-age=3600`) on served images.

## Assumptions

1. Images are placed into the volume by operators or external tooling -- the
   web server never writes to the volume.
2. The volume is readable by the `gofr-doc` user (uid/gid match or world-readable).
3. Image files are reasonably sized (stock images, logos, charts -- not
   multi-GB assets).
4. The MCP server does NOT need image-serving endpoints (web only).

## Open Questions

None -- all clarified via discussion.
