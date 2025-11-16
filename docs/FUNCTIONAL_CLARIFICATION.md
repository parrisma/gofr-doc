# Template vs Fragment: Functional Clarification

## Conceptual Distinction

### Templates = Document Structure
A **template** is the **container** that defines:
- Overall document shape and layout
- Global styling applied to the entire document
- Which types of content can be included
- The ordering constraints (if any)

**Analogy**: A template is like a newspaper layout—it defines sections, columns, header/footer regions, and fonts, but doesn't specify the actual articles.

**Examples**:
- `basic_report` — Professional report with title page, sections, conclusion
- `newsletter` — Magazine-like format with featured story, news items, sidebar
- `invoice` — Structured document with header, line items, totals, footer
- `technical_doc` — Multi-section documentation with table of contents

### Fragments = Content Blocks
A **fragment** is a **reusable piece of content** that represents:
- Specific types of information (news, index entries, data points)
- Structured parameters (headline, body, metadata)
- Self-contained rendering logic
- Content that can be composed into documents

**Analogy**: Fragments are like articles, photos, and ads in a newspaper—they're discrete pieces that fit into the layout defined by the template.

**Examples**:
- `index` — An index entry (title, page number, hierarchy level)
- `news_item` — A news story (headline, byline, body, date)
- `section` — A document section (heading, content, subsections)
- `sidebar` — Supplementary information (title, bullet points)
- `footer` — Page footer (copyright, page number)

## Functional Relationship

```
Template (Structure)
├── Defines global layout
├── Applies CSS styling
├── Sets global parameters (title, author, date)
└── Contains ordered fragments:
    ├── Fragment 1 (news_item: "Breaking News")
    ├── Fragment 2 (index: "Table of Contents")
    ├── Fragment 3 (section: "Analysis")
    └── Fragment N (footer: "Page X of Y")
```

## Key Differences

| Aspect | Template | Fragment |
|--------|----------|----------|
| **Scope** | Entire document | Single content block |
| **Reuse** | One per document session | Multiple instances in one doc |
| **Parameters** | Global (apply to whole doc) | Local (specific to that block) |
| **CSS** | Defines styling layer | Inherits template's styling |
| **Count** | 1 per session | 0 to N per session |
| **Lifecycle** | Created with session | Added/removed during assembly |

## Example Workflow

**1. Create session with template**
```json
POST /create_document_session
{
  "template_id": "newsletter"  // Defines: layout, CSS, global params
}
```

**2. Set global parameters**
```json
POST /set_global_parameters
{
  "session_id": "...",
  "parameters": {
    "title": "November 2025 Newsletter",
    "date": "2025-11-16",
    "issue": "42"
  }
}
```

**3. Add fragments (content)**
```json
POST /add_fragment
{
  "session_id": "...",
  "fragment_id": "news_item",  // "Breaking Product Launch"
  "parameters": {
    "headline": "We Released v2.0!",
    "byline": "Engineering Team",
    "body": "...",
    "date": "2025-11-16"
  }
}

POST /add_fragment
{
  "session_id": "...",
  "fragment_id": "news_item",  // Another news story
  "parameters": {
    "headline": "Record User Growth",
    "byline": "Product Team",
    "body": "..."
  }
}

POST /add_fragment
{
  "session_id": "...",
  "fragment_id": "sidebar",    // "In This Issue"
  "parameters": {
    "title": "In This Issue",
    "items": ["v2.0 Launch", "User Milestones", "Events"]
  }
}
```

**4. Render document**
```json
GET /render
{
  "session_id": "...",
  "format": "pdf",
  "style_id": "default"
}
```

Result: A PDF with the newsletter template layout + all added fragments, styled consistently with `default.css`.

## Registry Implications

### TemplateRegistry
Manages document **structures**:
- Loads templates from `templates/{template_id}/template.yaml`
- Validates global parameters
- Provides template discovery and details
- Manages Jinja2 document templates

### FragmentRegistry
Manages content **blocks**:
- Loads fragments from `fragments/{fragment_id}/fragment.yaml`
- Validates fragment-specific parameters
- Provides fragment discovery and details
- Manages Jinja2 fragment templates

### Shared Features
Both registries:
- Load YAML definitions
- Manage Jinja2 rendering
- Provide schema validation
- Support caching and discovery

## Rendering Engine Integration

The **rendering engine** orchestrates both:

1. **Load template** → Get document structure + CSS
2. **Inject global parameters** → Title, author, date, etc.
3. **Iterate fragments** → Render each fragment with local parameters
4. **Compose HTML** → Insert fragments into document template
5. **Apply style** → CSS from template styling
6. **Convert** → HTML → PDF/Markdown as needed

```
Rendering Pipeline:
┌─────────────────────────────────────┐
│ TemplateRegistry.get_template()     │ Load structure
└──────────┬──────────────────────────┘
           │
           v
┌─────────────────────────────────────┐
│ Inject global parameters            │
│ (title, author, date, etc.)         │
└──────────┬──────────────────────────┘
           │
           v
┌─────────────────────────────────────┐
│ For each session fragment:          │
│  - FragmentRegistry.get()           │ Load fragment schema
│  - Validate parameters              │
│  - Render with Jinja2               │ Generate fragment HTML
│  - Insert into document             │
└──────────┬──────────────────────────┘
           │
           v
┌─────────────────────────────────────┐
│ Apply StyleRegistry CSS             │
└──────────┬──────────────────────────┘
           │
           v
┌─────────────────────────────────────┐
│ Convert to output format            │
│ (PDF, Markdown, etc.)               │
└─────────────────────────────────────┘
```

## Test Structure Strategy

For `test/render/`, we'll create:

**Templates** (document structures):
- `basic_report` — Simple report (title + sections + conclusion)
- `newsletter` — Magazine format (featured + news items + sidebar)

**Fragments** (reusable content):
- `index` — Table of contents entry
- `news_item` — Article/story block
- `section` — Titled content section
- `sidebar` — Supplementary info box

**Styles** (CSS bundles):
- `default` — Professional/clean style
- `minimal` — Bare-bones for testing

This allows comprehensive rendering tests covering:
- Template structure validation
- Fragment parameter validation
- Fragment composition
- Style application
- Format conversion (HTML → PDF → Markdown)
