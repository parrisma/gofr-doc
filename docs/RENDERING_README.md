# Test Rendering Structure

This directory contains test fixtures for rendering tests.

## Functional Clarification

### Templates (Document Structure)
A template defines the **overall document structure** that inherits styles (CSS). Templates:
- Define the document layout and composition
- Specify global parameters (e.g., title, author, date)
- Declare which fragments can be included
- Apply styles uniformly via CSS

Examples: `basic_report`, `newsletter`, `invoice`, `technical_doc`

### Fragments (Content Blocks)
Fragments are **reusable content blocks** that can be inserted into templates. Fragments:
- Represent specific content types (e.g., index, news item, section)
- Have their own parameters
- Are composed together within a document
- Follow the template's styling

Examples: `index`, `news_item`, `section`, `sidebar`, `footer`, `paragraph`

## Directory Structure

```
test/render/
├── data/
│   └── docs/
│       ├── templates/          # Document structure definitions
│       │   └── basic_report/   # Example template
│       │       ├── template.yaml
│       │       └── document.html.jinja2
│       ├── fragments/          # Standalone content blocks
│       │   ├── index/
│       │   ├── news_item/
│       │   └── section/
│       └── styles/             # Style bundles
│           └── default/
└── conftest.py                 # Pytest fixtures
```

## Example Files

### Template Structure
```yaml
# templates/basic_report/template.yaml
template_id: basic_report
name: Basic Report
description: Simple report with sections and content blocks
global_parameters:
  - name: title
    type: string
    description: Document title
    required: true
  - name: author
    type: string
    description: Document author
    required: false
```

### Fragment Structure
```yaml
# fragments/news_item/fragment.yaml
fragment_id: news_item
name: News Item
description: A news story with headline and content
parameters:
  - name: headline
    type: string
    description: News headline
    required: true
  - name: content
    type: string
    description: News story body
    required: true
  - name: date
    type: string
    description: Publication date
    required: false
```

## Next Steps (Waiting)

A. ✅ Create test/render directory structure
B. ✅ Create data/docs structure with templates, fragments, styles folders
C. ⏳ Awaiting next instructions for creating test templates and fragments
