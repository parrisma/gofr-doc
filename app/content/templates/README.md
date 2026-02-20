# Group-scoped templates (master content)

This folder is the source-of-truth for template content.
In container/test runs, content from app/content/templates is copied into the runtime data directory.

On disk, templates are organized by group.

## Layout

Each immediate subdirectory under this folder is treated as a group name.

Structure:

- app/content/templates/
  - public/
    - <template_id>/
      - template.yaml
      - document.html.jinja2
      - fragments/
        - <fragment_id>.html.jinja2
  - <group_name>/
    - <template_id>/
      - template.yaml
      - document.html.jinja2
      - fragments/
        - <fragment_id>.html.jinja2

Notes:
- Group directories starting with '_' are ignored.
- A template is identified by metadata.template_id in template.yaml.
- metadata.group in template.yaml must match the group directory name.

## Public vs private templates

- public/
  - Intended for templates usable without special group membership.
  - Many flows default to the public group when no authenticated group is present.

- <group_name>/
  - Intended for templates dedicated to a specific group.
  - In authenticated MCP/web flows, the caller group comes from the auth token.

In practice, a "private" template is one that exists only under a non-public group directory and has metadata.group set to that group.

## Adding a dedicated group template

1) Create the group directory:
- app/content/templates/<group_name>/

2) Add a template folder:
- app/content/templates/<group_name>/<template_id>/

3) Provide required files:
- template.yaml (with metadata.template_id and metadata.group)
- document.html.jinja2
- fragments/*.html.jinja2 for any fragment_id declared in template.yaml

## Deployment note

Some deployments also expose templates via data/templates (often as a symlink or copy of this directory).
When in doubt, edit app/content/templates first.
