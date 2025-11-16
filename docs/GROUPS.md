# Template, Fragment, and Style Groups

## Overview

Doco's group system provides organization and isolation of templates, fragments, and styles into logical collections. Groups allow you to:

- **Organize Resources**: Group related templates, fragments, and styles together (e.g., "public", "internal", "research")
- **Isolate Access**: Prevent cross-group references and ensure clean separation of concerns
- **Filter Resources**: Query and display items by group via CLI and API
- **Manage Metadata**: Track which group each resource belongs to for multi-tenant scenarios

Every template, fragment, and style belongs to exactly one group. By default, the `public` group is created for all items.

## Directory Structure

### Before (Flat Structure)

```
templates/
  ├── basic_report/
  ├── detailed_report/
  └── monthly_summary/

fragments/
  ├── news_item/
  ├── event_notice/
  └── announcement/

styles/
  ├── default/
  └── minimal/
```

### After (Grouped Structure)

```
templates/
  └── public/
      ├── basic_report/
      ├── detailed_report/
      └── monthly_summary/
  └── research/
      ├── research_paper/
      └── findings_summary/

fragments/
  └── public/
      ├── news_item/
      ├── event_notice/
      └── announcement/
  └── internal/
      ├── employee_bio/
      └── department_update/

styles/
  └── public/
      ├── default/
      └── minimal/
  └── corporate/
      └── branded/
```

## Resource Metadata

Every resource must declare its group in its metadata file. The group must match the directory structure.

### Template Metadata Example

```yaml
metadata:
  name: "Basic Report"
  description: "A simple report with title and content sections"
  version: "1.0"
  group: "public"  # Mandatory - must match directory
  
global_parameters:
  - name: "title"
    type: "string"
    required: true
```

### Fragment Metadata Example

```yaml
metadata:
  name: "News Item"
  description: "A news story with headline, byline, and body"
  group: "public"  # Mandatory - must match directory
  
parameters:
  - name: "headline"
    type: "string"
    required: true
```

### Style Metadata Example

```yaml
metadata:
  name: "Default Style"
  description: "Default CSS styling"
  group: "public"  # Mandatory - must match directory
```

## Using Groups

### CLI Commands

#### List All Groups

```bash
# Show all groups
python scripts/render_manager.py groups

# Show groups with statistics
python scripts/render_manager.py groups -v
```

Output:
```
Group                Templates    Fragments    Styles
------------------------------------------------------------
public               3            5            2
research             2            1            0
internal             0            2            1
```

#### List Resources by Group

```bash
# List all templates
python scripts/render_manager.py templates list

# List templates in specific group
python scripts/render_manager.py templates list --group public

# With verbose output
python scripts/render_manager.py templates list --group public -v
```

#### Fragment Operations

```bash
# List all standalone fragments
python scripts/render_manager.py fragments list

# List fragments in specific group
python scripts/render_manager.py fragments list --group internal -v

# Get fragment details
python scripts/render_manager.py fragments info news_item
```

#### Storage Management by Group

```bash
# List all stored images
python scripts/storage_manager.py list

# List images in specific group
python scripts/storage_manager.py list --group research -v

# Show storage statistics
python scripts/storage_manager.py stats

# Show statistics for specific group
python scripts/storage_manager.py stats --group public

# Purge old images from specific group
python scripts/storage_manager.py purge --age-days 30 --group research

# Purge all images in a group (requires confirmation)
python scripts/storage_manager.py purge --age-days 0 --group test_group
```

### Python API

#### Working with Registries

```python
from app.templates.registry import TemplateRegistry
from app.logger import session_logger

# Create registry
registry = TemplateRegistry('/path/to/templates', session_logger)

# List all groups
groups = registry.list_groups()
print(groups)  # ['public', 'research', 'internal']

# Get items by group
public_templates = registry.list_templates(group='public')
research_templates = registry.list_templates(group='research')

# Get all items with group info
all_templates = registry.list_templates()
for tmpl in all_templates:
    print(f"{tmpl.template_id} ({tmpl.group})")

# Get items organized by group
public_items = registry.get_items_by_group('public')
for item in public_items:
    print(f"  {item.template_id}")
```

#### Template Group Inheritance

When a template is loaded, its embedded fragments automatically inherit the template's group:

```python
# Template 'basic_report' is in 'public' group
schema = registry.get_template_schema('basic_report')

# All embedded fragments get public group from template
for fragment in schema.fragments:
    print(f"{fragment.fragment_id} in group: {fragment.group}")
    # Output: paragraph in group: public
    # Output: data_table in group: public
```

## Migration from Flat Structure

When you first run Doco with the grouped structure, the system automatically migrates any existing flat structure:

### Automatic Migration

1. **Detection**: System detects flat structure (resources not in subdirectories)
2. **Migration**: All items are moved to the `public` group subdirectory
3. **Metadata Update**: YAML metadata is updated to include `group: "public"`
4. **Validation**: Groups are validated against directory structure

### Migration Example

```
Before:
  templates/
    └── basic_report/

After:
  templates/
    └── public/
        └── basic_report/
          (metadata.group now set to "public")
```

### Manual Migration

If you want to create additional groups manually:

1. Create group subdirectory:
   ```bash
   mkdir -p templates/research
   mkdir -p fragments/research
   mkdir -p styles/corporate
   ```

2. Move resources:
   ```bash
   mv templates/research_paper templates/research/
   mv templates/findings_summary templates/research/
   ```

3. Update metadata files to set `group: "research"` in YAML

4. Restart the application

## Error Handling

### Group Mismatch Error

Occurs when metadata.group doesn't match directory location:

```yaml
# ❌ ERROR: metadata says 'public' but file is in 'research' directory
templates/research/my_template/template.yaml
metadata:
  group: "public"  # Wrong!
```

**Resolution**: Update metadata to match directory:
```yaml
metadata:
  group: "research"  # Correct
```

### Missing Group Field Error

Occurs when resource metadata doesn't declare a group:

```yaml
# ❌ ERROR: Missing mandatory 'group' field
metadata:
  name: "My Template"
  # group: ???
```

**Resolution**: Add group declaration:
```yaml
metadata:
  name: "My Template"
  group: "public"  # Add mandatory field
```

### Group Not Found Error

Occurs when trying to access a non-existent group:

```python
# ❌ ERROR: 'nonexistent' group doesn't exist
templates = registry.list_templates(group='nonexistent')
```

**Resolution**: Use valid group names from `list_groups()`:
```python
valid_groups = registry.list_groups()  # ['public', 'research']
templates = registry.list_templates(group='public')  # ✅ Valid
```

## Design Decisions

The groups system was designed with these principles:

### 1. **Mandatory Declaration**
Every resource must explicitly declare its group in metadata. There are no implicit or global defaults per resource (though "public" is the semantic default group name).

### 2. **Group-Directory Match Enforcement**
The metadata `group` field must match the directory structure: `{registry_type}/{group}/{item_id}/`. This is validated at registration time.

### 3. **Implicit Fragment References**
Fragments referenced in templates use only their ID. The template's group is implicitly searched, avoiding the need to repeat group specifications in references.

### 4. **Embedded Fragment Inheritance**
When a template is loaded, its embedded fragments automatically inherit the template's group assignment at schema build time, not as separate registry items.

### 5. **No Fragment Nesting**
Fragments cannot contain other fragments. Only templates can embed fragments. This keeps the fragment dependency graph simple.

### 6. **Lazy Validation**
Fragment validation (checking that referenced fragments exist) happens at render time, not at registration time. This allows flexible iteration during development.

### 7. **Auto-Migration**
The system automatically migrates flat structures to grouped ones on first run. All items move to the "public" group with YAML metadata updated accordingly.

### 8. **Group-Aware CLI and Storage**
Both render_manager and storage_manager support group filtering via `--group` flag for consistent user experience.

## Future Enhancements

### Access Control (Planned)

Future versions will add access control based on groups:

```python
# Example (not yet implemented)
user = get_current_user()
allowed_groups = user.get_allowed_groups()  # ['public', 'research']

# Only see items in allowed groups
templates = registry.list_templates(allowed_groups=allowed_groups)
```

### Group Metadata (Planned)

Store additional metadata about groups themselves:

```yaml
# groups/public/group.yaml (future)
name: "Public Group"
description: "Publicly available templates and fragments"
visibility: "public"
owner: "platform_team"
created_at: "2025-01-01"
```

### Cross-Group Composition (Planned)

Allow explicit cross-group references with access control:

```yaml
# templates/research/analysis.yaml (future)
fragments:
  - id: chart_widget
    group: public  # Explicitly reference from different group
```

## Troubleshooting

### Why can't I find my template?

1. Check if you're filtering by group: `--group public`
2. Verify the template is in the correct directory structure
3. Verify metadata.group matches the directory path
4. Use `render_manager.py groups -v` to see what groups exist

### Template parameters won't validate

1. Ensure group is set in metadata: `group: "public"`
2. Check that metadata.group matches the directory
3. Verify no typos in group names

### Migration didn't work

1. Check error messages in logs
2. Ensure all YAML files have proper syntax
3. Verify write permissions to directories
4. Check that group directories exist before moving files

### Images not appearing in storage stats by group

1. Check that images are properly tagged with group metadata
2. Use `storage_manager.py list --group <name> -v` to verify
3. Ensure storage metadata files are intact

## See Also

- [RENDERING_README.md](./RENDERING_README.md) - Template and fragment rendering
- [FRAGMENT_REGISTRY_DESIGN.md](./FRAGMENT_REGISTRY_DESIGN.md) - Fragment system design
- [DATA_PERSISTENCE.md](./DATA_PERSISTENCE.md) - Storage and persistence
