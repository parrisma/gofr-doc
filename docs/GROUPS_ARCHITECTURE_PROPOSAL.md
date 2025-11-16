# Groups Architecture Design Proposal

## Overview

Introduce a **group-based separation system** for templates and fragments to enable:
- Public templates/fragments accessible to all
- Private/restricted groups for organization-specific or team-specific content
- Clear separation at both the code level (registries) and storage level (filesystem)

---

## Current State

```
templates/
├── basic_report/
│   ├── template.yaml
│   └── document.html.jinja2
└── (other templates)

fragments/
├── news_item/
│   ├── fragment.yaml
│   └── fragment.html.jinja2
└── (other fragments)
```

**Issue**: All templates/fragments are mixed together with no organizational separation.

---

## Proposed Design

### A. Directory Structure (Storage Level)

```
templates/
├── public/                    # Default group (always accessible)
│   ├── basic_report/
│   │   ├── template.yaml
│   │   └── document.html.jinja2
│   └── (other public templates)
├── research/                  # Custom group
│   ├── lab_report/
│   │   ├── template.yaml
│   │   └── document.html.jinja2
│   └── (other research templates)
└── finance/                   # Custom group
    └── (finance-specific templates)

fragments/
├── public/                    # Default group
│   ├── news_item/
│   │   ├── fragment.yaml
│   │   └── fragment.html.jinja2
│   └── (other public fragments)
├── research/                  # Custom group
│   └── (research-specific fragments)
└── finance/                   # Custom group
    └── (finance-specific fragments)
```

**Key Points:**
- Always include `public/` group (default, always accessible)
- Groups are directories at the top level of templates/ and fragments/
- Each group contains its own set of templates/fragments with identical structure
- Groups are self-contained and independent

### B. Registry API Changes

#### TemplateRegistry

**Current:**
```python
registry = TemplateRegistry(templates_dir, logger)
templates = registry.list_templates()
schema = registry.get_template_schema(template_id)
```

**Proposed:**
```python
# Option 1: Single group initialization
registry = TemplateRegistry(templates_dir, logger, group="public")
templates = registry.list_templates()  # Only public templates
schema = registry.get_template_schema(template_id)

# Option 2: Multi-group initialization
registry = TemplateRegistry(templates_dir, logger, groups=["public", "research"])
templates = registry.list_templates()  # All templates from public + research
schema = registry.get_template_schema(template_id)  # Searches across groups

# Option 3: Access specific group
registry = TemplateRegistry(templates_dir, logger)  # Load all groups
templates = registry.list_templates(group="public")  # Filter by group
templates_all = registry.list_templates()  # All groups
```

#### FragmentRegistry

Same pattern as TemplateRegistry:
```python
registry = FragmentRegistry(fragments_dir, logger, group="public")
fragments = registry.list_fragments()
schema = registry.get_fragment_schema(fragment_id)
```

### C. Metadata Changes

#### template.yaml
```yaml
metadata:
  template_id: basic_report
  group: public                    # NEW: Explicit group declaration
  name: Basic Report
  description: A simple report
  version: "1.0.0"

global_parameters: [...]
fragments: [...]
```

#### fragment.yaml
```yaml
fragment_id: news_item
group: public                       # NEW: Explicit group declaration
name: News Item
description: A news story
parameters: [...]
```

**Why explicit group in YAML?**
- Validation: Ensures fragment is in correct group directory
- Migration: Easy to detect misplaced files
- Self-documenting: Metadata is complete without guessing from directory

### D. BaseRegistry Updates

```python
class BaseRegistry(ABC):
    def __init__(self, registry_dir: str, logger: Logger, 
                 group: Optional[str] = None, 
                 groups: Optional[List[str]] = None):
        """
        Args:
            registry_dir: Base directory (templates/ or fragments/)
            logger: Logger instance
            group: Single group to load (e.g., "public")
            groups: Multiple groups to load (e.g., ["public", "research"])
        """
        self.registry_dir = Path(registry_dir)
        self.groups = self._resolve_groups(group, groups)  # ["public"] or ["public", "research"]
        self.logger = logger
        self._jinja_env: Optional[Environment] = None
        self._setup_jinja_env()
        self._load_items()

    def _resolve_groups(self, group: Optional[str], groups: Optional[List[str]]) -> List[str]:
        """Determine which groups to load."""
        if groups:
            return groups
        if group:
            return [group]
        # Default: Load all groups found in directory
        return self._discover_groups()

    def _discover_groups(self) -> List[str]:
        """Find all group directories."""
        groups = []
        for item in self.registry_dir.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                groups.append(item.name)
        return sorted(groups) or ["public"]

    def _load_items(self) -> None:
        """Load items from specified groups."""
        for group in self.groups:
            self._load_group_items(group)

    def _load_group_items(self, group: str) -> None:
        """Load all items from a specific group."""
        group_dir = self.registry_dir / group
        if not group_dir.exists():
            self.logger.warning(f"Group '{group}' directory not found")
            return
        # Load items from group_dir...
```

### E. Registry Methods

#### List with group filtering

```python
def list_templates(self, group: Optional[str] = None) -> List[TemplateListItem]:
    """
    List templates.
    
    Args:
        group: Filter by specific group (None = all loaded groups)
    """
    if group:
        if group not in self.groups:
            return []
        return [t for t in self._templates.values() if t.metadata.group == group]
    return list(self._templates.values())

def get_template_schema(self, template_id: str, group: Optional[str] = None) -> Optional[TemplateSchema]:
    """Get template schema, optionally filtered by group."""
    for tmpl in self._templates.values():
        if tmpl.metadata.template_id == template_id:
            if group is None or tmpl.metadata.group == group:
                return tmpl
    return None

def list_groups(self) -> List[str]:
    """Return list of loaded groups."""
    return self.groups

def get_items_by_group(self) -> Dict[str, List]:
    """Get all templates/fragments organized by group."""
    result = {group: [] for group in self.groups}
    for item in self._templates.values():
        result[item.metadata.group].append(item)
    return result
```

### F. MCP/CLI Integration

#### render_manager.py additions

```bash
# List templates from specific group
python render_manager.py --group public templates list

# List all templates from all accessible groups
python render_manager.py templates list

# Get template details with group context
python render_manager.py --group research templates info lab_report

# List available groups
python render_manager.py groups list
```

#### MCP Server

```python
# When creating session
create_document_session(
    template_id="basic_report",
    group="public"  # NEW: Optional, defaults to "public"
)

# Discovery tools return group info
list_templates(group="public")  # Filter by group
list_groups()                    # NEW: List available groups
```

### G. Jinja2 Template Path Resolution

**Current:**
```
templates/basic_report/document.html.jinja2  →  basic_report/document.html.jinja2
```

**Proposed:**
```
templates/public/basic_report/document.html.jinja2  →  public/basic_report/document.html.jinja2
```

Jinja2 FileSystemLoader points to `templates/` and searches `public/basic_report/document.html.jinja2`.

---

## Implementation Plan

### Phase 1: Core Registry Changes
1. Update `BaseRegistry` with group support
2. Update `TemplateRegistry` to handle groups
3. Update `FragmentRegistry` to handle groups
4. Update document models with `group` field in metadata

### Phase 2: Storage Migration
1. Create group directories
2. Move existing templates/fragments to `public/` directory
3. Validate metadata includes group field

### Phase 3: CLI Updates
1. Add `--group` flag to `render_manager.py`
2. Add `groups list` command
3. Update help/examples

### Phase 4: Testing
1. Create test fixtures with multiple groups
2. Test group isolation
3. Test default group ("public")
4. Test multi-group loading

### Phase 5: API Integration
1. Update MCP server tools
2. Add group parameter to create_document_session
3. Update session storage with group context

---

## Backward Compatibility

**Migration Strategy:**
1. If templates/ doesn't have group directories, treat as `public/`
2. Auto-migrate: If item lacks `group` metadata, assume `public`
3. Deprecation: Log warnings for items without explicit group
4. Eventually: Require explicit group in metadata

---

## Security Considerations

1. **Access Control**: Group membership determined at initialization time
2. **No Cross-Group Access**: Items from "research" group not accessible if not in loaded groups
3. **User → Group Mapping**: Application layer maps JWT user → allowed groups
4. **Metadata Validation**: Verify item group matches directory location

---

## Example Scenarios

### Scenario 1: Public Templates Only
```python
registry = TemplateRegistry(templates_dir, logger, group="public")
templates = registry.list_templates()  # Only public templates
```

### Scenario 2: Multi-Tenant System
```python
# User belongs to "research" and "public" groups
registry = TemplateRegistry(templates_dir, logger, groups=["public", "research"])
templates = registry.list_templates()  # Both groups
```

### Scenario 3: Default to All
```python
registry = TemplateRegistry(templates_dir, logger)  # No group specified
all_groups = registry.list_groups()  # ["finance", "public", "research"]
public_only = registry.list_templates(group="public")
```

---

## Discussion Points (RESOLVED)

1. **Should group be mandatory in metadata?** → **YES, ALWAYS** (not optional). Every template/fragment must declare its group
2. **How to handle template references to fragments?** → **Templates can ONLY reference fragments in their OWN group** (group-relative access)
3. **Can fragments span groups?** → **NO** - fragments must be wholly contained within a single group directory
4. **Can templates span groups?** → **NO** - templates must be wholly contained within a single group directory
5. **Cross-group interaction?** → **NONE** - no cross-group access, no inter-group references
6. **Default group name?** → "public" (semantic clarity)
7. **Group discovery automatic?** → Yes, scan directory for group folders
8. **Can users create new groups?** → Yes, at filesystem level (admin responsibility)

---

## CLARIFICATION QUESTIONS FOR USER

Before implementing, need confirmation on:

### Q1: Fragment References in Templates ✅ DECIDED
When a template (e.g., in `public/` group) references a fragment in its metadata:

**Decision: IMPLICIT**
```yaml
# templates/public/report/template.yaml
metadata:
  template_id: report
  group: public

fragments:
  - fragment_id: paragraph      # Implicit: search in public/ only
    parameters: {}
```

Fragment references use fragment_id only. Registry searches ONLY within the template's own group. If fragment not found in same group → Error (see Q5).

---

### Q2: Access Control at Registry Level ✅ DECIDED
You mentioned groups will be "access controlled" in future. Should registries:

**Decision: LAZY LOAD on demand (access control added in future)**
```python
# NOW: Load all available groups
registry = TemplateRegistry(templates_dir, logger)  # Discovers all groups
templates = registry.list_templates()  # Returns all templates from all groups

# FUTURE: Access control layer
registry = TemplateRegistry(templates_dir, logger, groups=["public"])  # Load public only
templates = registry.list_templates()  # Only public templates
```

Registry discovers and loads all groups present in the directory. In future, before loading groups, an access control check will determine which groups a user is allowed to access. For now, no access filtering happens at registry level.

---

### Q3: Fragment Validation in Templates ✅ DECIDED

**Decision: LAZY validation**

When loading a template, do NOT validate that referenced fragments exist in the same group. Validation happens at render time when the fragment is actually needed. This allows:
- Templates to be created before all fragments exist
- Clearer error messages at the point of failure (during rendering, not schema load)

---

### Q4: Metadata Consistency Check ✅ DECIDED

**Decision: YES - Enforce strict group/directory match**

When loading a template or fragment:
- `templates/public/report/template.yaml` MUST contain `group: public` in metadata
- `fragments/research/analysis/fragment.yaml` MUST contain `group: research` in metadata
- **Error if mismatch**: Example: metadata says `group: research` but file is in `templates/public/`

Error message example: `"Template 'report' in directory 'templates/public/' declares group 'research' - group must match directory location. Expected group: 'public'"`

---

### Q5: Error Handling Strategy ✅ DECIDED

**Decision: Return EXPLICIT ERROR with clear details (not just None)**

When `registry.get_template_schema(template_id)` fails:
- **If template doesn't exist**: `TemplateNotFoundError(f"Template '{template_id}' not found in any loaded group")`
- **If fragment reference missing in same group**: `FragmentNotFoundError(f"Fragment '{fragment_id}' referenced by template '{template_id}' not found in group '{group}'. Available fragments in group '{group}': {list_of_fragments}")`
- **If group/directory mismatch detected**: `GroupMismatchError(f"Template '{template_id}' in directory '{expected_group}/' declares group '{actual_group}' - metadata group must match directory location")`

**Why explicit errors?** These error messages will be passed to an LLM that needs to make decisions and take actions. Clear, detailed error messages enable intelligent error recovery and user guidance.

---

### Q6: Backward Compatibility ✅ DECIDED

**Decision: AUTO-MIGRATE (one-time migration)**

When the registry is initialized:
1. Check if `templates/` root contains any template directories (flat structure)
2. If found, automatically move them to `templates/public/{template_id}/`
3. Add `group: public` to their metadata files
4. Log the migration: "Migrated template 'basic_report' to group 'public'"
5. Same process for fragments: `fragments/` → `fragments/public/`

**Migration Behavior:**
- One-time automatic migration (happens on first registry initialization)
- Preserves all template/fragment content and functionality
- Makes group structure explicit in metadata
- Logs all migrations for audit trail
- After migration, strict group structure is enforced

---

### Q7: Styles Directory ✅ DECIDED

**Decision: Styles ARE group-aware**

```
styles/
├── public/
│   ├── default/
│   │   ├── style.yaml
│   │   └── style.css
│   └── professional/
│       ├── style.yaml
│       └── style.css
├── research/
│   └── scientific/
│       ├── style.yaml
│       └── style.css
└── finance/
    └── corporate/
        ├── style.yaml
        └── style.css
```

Styles follow the same group structure as templates and fragments. Each style must declare its group in `style.yaml`. Templates can only reference styles in their own group.

---

### Q8: Fragment Nesting ✅ DECIDED

**Decision: Fragments are flat/standalone - NO nesting**

Fragments cannot reference other fragments. Each fragment is a complete, self-contained unit. Templates embed fragments, but fragments do not embed other fragments. This keeps the architecture simple and prevents circular dependencies.

---

## Summary of Design Decisions

✅ **Q1: Fragment references** - Implicit (fragment_id only, searches current group)
✅ **Q2: Access control** - Lazy load all groups now, add access filtering in future
✅ **Q3: Fragment validation** - Lazy (validate at render time, not schema load)
✅ **Q4: Group/directory match** - Strict enforcement with clear error messages
✅ **Q5: Error handling** - Explicit errors with context for LLM processing
✅ **Q6: Backward compatibility** - AUTO-MIGRATE flat structure to public/ on first init
✅ **Q7: Styles directory** - Group-aware, same structure as templates/fragments
✅ **Q8: Fragment nesting** - NO, fragments are flat/standalone

---

## Design Complete - Ready for Implementation

All design decisions are now locked in. The groups architecture is fully specified with:
- Complete metadata requirements (mandatory `group` field)
- Directory structure (grouped: `templates/{group}/{template_id}/`)
- Registry API (implicit fragment references, lazy validation)
- Error handling (explicit errors for LLM processing)
- Backward compatibility (one-time auto-migration to public/ group)
- Access control foundation (lazy load groups now, add filtering in future)

Proceeding to implementation phases.
