"""Test rendering with templates, fragments, and styles."""
import pytest
from pathlib import Path
from app.templates.registry import TemplateRegistry
from app.fragments.registry import FragmentRegistry
from app.styles.registry import StyleRegistry
from app.logger import ConsoleLogger


@pytest.fixture
def test_data_dir():
    """Get the test data directory."""
    return Path(__file__).parent / "data/docs"


@pytest.fixture
def logger():
    """Get a logger instance."""
    return ConsoleLogger()


@pytest.fixture
def template_registry(test_data_dir, logger):
    """Initialize template registry with test fixtures."""
    return TemplateRegistry(str(test_data_dir / "templates"), logger)


@pytest.fixture
def fragment_registry(test_data_dir, logger):
    """Initialize fragment registry with test fixtures."""
    return FragmentRegistry(str(test_data_dir / "fragments"), logger)


class TestTemplateRegistry:
    """Test template registry functionality."""

    def test_list_templates(self, template_registry):
        """Test listing available templates."""
        templates = template_registry.list_templates()
        assert len(templates) > 0
        assert any(t.template_id == "basic_report" for t in templates)

    def test_get_template_schema(self, template_registry):
        """Test retrieving template schema."""
        schema = template_registry.get_template_schema("basic_report")
        assert schema is not None
        assert schema.metadata.template_id == "basic_report"
        assert len(schema.global_parameters) > 0

    def test_get_template_details(self, template_registry):
        """Test retrieving template details."""
        details = template_registry.get_template_details("basic_report")
        assert details is not None
        assert details.template_id == "basic_report"
        assert len(details.global_parameters) > 0

    def test_template_exists(self, template_registry):
        """Test template existence check."""
        assert template_registry.template_exists("basic_report")
        assert not template_registry.template_exists("nonexistent")

    def test_get_fragment_schema(self, template_registry):
        """Test retrieving fragment schema from template."""
        fragment = template_registry.get_fragment_schema("basic_report", "paragraph")
        assert fragment is not None
        assert fragment.fragment_id == "paragraph"

    def test_validate_global_parameters_valid(self, template_registry):
        """Test parameter validation with valid parameters."""
        is_valid, errors = template_registry.validate_global_parameters(
            "basic_report",
            {"title": "Test Report", "author": "Test Author"}
        )
        assert is_valid
        assert len(errors) == 0

    def test_validate_global_parameters_missing_required(self, template_registry):
        """Test parameter validation with missing required parameters."""
        is_valid, errors = template_registry.validate_global_parameters(
            "basic_report",
            {"author": "Test Author"}
        )
        assert not is_valid
        assert len(errors) > 0

    def test_validate_fragment_parameters_valid(self, template_registry):
        """Test fragment parameter validation with valid parameters."""
        is_valid, errors = template_registry.validate_fragment_parameters(
            "basic_report",
            "paragraph",
            {"text": "Some text"}
        )
        assert is_valid
        assert len(errors) == 0

    def test_validate_fragment_parameters_missing_required(self, template_registry):
        """Test fragment parameter validation with missing required parameters."""
        is_valid, errors = template_registry.validate_fragment_parameters(
            "basic_report",
            "paragraph",
            {}
        )
        assert not is_valid
        assert len(errors) > 0


class TestFragmentRegistry:
    """Test fragment registry functionality."""

    def test_list_fragments(self, fragment_registry):
        """Test listing available fragments."""
        fragments = fragment_registry.list_fragments()
        assert len(fragments) > 0
        assert any(f["fragment_id"] == "news_item" for f in fragments)

    def test_get_fragment_schema(self, fragment_registry):
        """Test retrieving fragment schema."""
        schema = fragment_registry.get_fragment_schema("news_item")
        assert schema is not None
        assert schema.fragment_id == "news_item"

    def test_fragment_exists(self, fragment_registry):
        """Test fragment existence check."""
        assert fragment_registry.fragment_exists("news_item")
        assert not fragment_registry.fragment_exists("nonexistent")

    def test_validate_parameters_valid(self, fragment_registry):
        """Test parameter validation with valid parameters."""
        is_valid, errors = fragment_registry.validate_parameters(
            "news_item",
            {"headline": "Breaking News", "body": "News content"}
        )
        assert is_valid
        assert len(errors) == 0

    def test_validate_parameters_missing_required(self, fragment_registry):
        """Test parameter validation with missing required parameters."""
        is_valid, errors = fragment_registry.validate_parameters(
            "news_item",
            {"headline": "Breaking News"}
        )
        assert not is_valid
        assert len(errors) > 0


class TestJinjaTemplateLoading:
    """Test Jinja2 template loading."""

    def test_load_document_template(self, template_registry):
        """Test loading document template."""
        template = template_registry.get_jinja_template("basic_report", "document.html.jinja2")
        assert template is not None

    def test_load_fragment_template(self, template_registry):
        """Test loading fragment template from template."""
        template = template_registry.get_jinja_template("basic_report", "fragments/paragraph.html.jinja2")
        assert template is not None

    def test_load_standalone_fragment_template(self, fragment_registry):
        """Test loading standalone fragment template."""
        template = fragment_registry.get_jinja_template("news_item")
        assert template is not None


# ============================================================================
# GROUP FUNCTIONALITY TESTS
# ============================================================================

class TestGroupDiscovery:
    """Test group discovery in registries."""

    def test_discover_groups_templates(self, test_data_dir, logger):
        """Test discovering available groups in templates."""
        registry = TemplateRegistry(str(test_data_dir / "templates"), logger)
        groups = registry.list_groups()
        assert "public" in groups

    def test_discover_groups_fragments(self, test_data_dir, logger):
        """Test discovering available groups in fragments."""
        registry = FragmentRegistry(str(test_data_dir / "fragments"), logger)
        groups = registry.list_groups()
        assert "public" in groups

    def test_discover_groups_styles(self, test_data_dir, logger):
        """Test discovering available groups in styles."""
        registry = StyleRegistry(str(test_data_dir / "styles"), logger)
        groups = registry.list_groups()
        assert "public" in groups


class TestGroupIsolation:
    """Test group isolation (no cross-group access)."""

    def test_single_group_template_loading(self, test_data_dir, logger):
        """Test loading templates from a single group."""
        registry = TemplateRegistry(
            str(test_data_dir / "templates"), 
            logger, 
            group="public"
        )
        templates = registry.list_templates()
        assert len(templates) > 0
        # All templates should be from public group
        for template in templates:
            assert template.group == "public"

    def test_single_group_fragment_loading(self, test_data_dir, logger):
        """Test loading fragments from a single group."""
        registry = FragmentRegistry(
            str(test_data_dir / "fragments"),
            logger,
            group="public"
        )
        fragments = registry.list_fragments()
        assert len(fragments) > 0
        # All fragments should be from public group
        for fragment in fragments:
            assert fragment["group"] == "public"

    def test_single_group_style_loading(self, test_data_dir, logger):
        """Test loading styles from a single group."""
        registry = StyleRegistry(
            str(test_data_dir / "styles"),
            logger,
            group="public"
        )
        styles = registry.list_styles()
        assert len(styles) > 0
        # All styles should be from public group
        for style in styles:
            assert style.group == "public"

    def test_filter_templates_by_group(self, test_data_dir, logger):
        """Test filtering templates by group."""
        registry = TemplateRegistry(str(test_data_dir / "templates"), logger)
        
        all_templates = registry.list_templates()
        public_templates = registry.list_templates(group="public")
        
        # Public should be a subset of all
        assert len(public_templates) <= len(all_templates)
        assert all(t.group == "public" for t in public_templates)

    def test_filter_fragments_by_group(self, test_data_dir, logger):
        """Test filtering fragments by group."""
        registry = FragmentRegistry(str(test_data_dir / "fragments"), logger)
        
        all_fragments = registry.list_fragments()
        public_fragments = registry.list_fragments(group="public")
        
        # Public should be a subset of all
        assert len(public_fragments) <= len(all_fragments)
        assert all(f["group"] == "public" for f in public_fragments)

    def test_filter_styles_by_group(self, test_data_dir, logger):
        """Test filtering styles by group."""
        registry = StyleRegistry(str(test_data_dir / "styles"), logger)
        
        all_styles = registry.list_styles()
        public_styles = registry.list_styles(group="public")
        
        # Public should be a subset of all
        assert len(public_styles) <= len(all_styles)
        assert all(s.group == "public" for s in public_styles)


class TestGetItemsByGroup:
    """Test get_items_by_group functionality."""

    def test_get_templates_by_group(self, test_data_dir, logger):
        """Test retrieving templates organized by group."""
        registry = TemplateRegistry(str(test_data_dir / "templates"), logger)
        items_by_group = registry.get_items_by_group()
        
        # Should have public group
        assert "public" in items_by_group
        # Public group should have items
        assert len(items_by_group["public"]) > 0
        # All items in public group should have group=public
        assert all(t.group == "public" for t in items_by_group["public"])

    def test_get_fragments_by_group(self, test_data_dir, logger):
        """Test retrieving fragments organized by group."""
        registry = FragmentRegistry(str(test_data_dir / "fragments"), logger)
        items_by_group = registry.get_items_by_group()
        
        # Should have public group
        assert "public" in items_by_group
        # Public group should have items
        assert len(items_by_group["public"]) > 0
        # All items in public group should have group=public
        assert all(f["group"] == "public" for f in items_by_group["public"])

    def test_get_styles_by_group(self, test_data_dir, logger):
        """Test retrieving styles organized by group."""
        registry = StyleRegistry(str(test_data_dir / "styles"), logger)
        items_by_group = registry.get_items_by_group()
        
        # Should have public group
        assert "public" in items_by_group
        # Public group should have items
        assert len(items_by_group["public"]) > 0
        # All items in public group should have group=public
        assert all(s.group == "public" for s in items_by_group["public"])


class TestMetadataGroupValidation:
    """Test that metadata group matches directory location."""

    def test_template_metadata_group_validation(self, test_data_dir, logger):
        """Test that template metadata group matches directory."""
        registry = TemplateRegistry(str(test_data_dir / "templates"), logger)
        
        # Get a template and verify its group matches directory
        schema = registry.get_template_schema("basic_report")
        assert schema is not None
        assert schema.metadata.group == "public"

    def test_fragment_metadata_group_validation(self, test_data_dir, logger):
        """Test that fragment metadata group matches directory."""
        registry = FragmentRegistry(str(test_data_dir / "fragments"), logger)
        
        # Get a fragment and verify its group matches directory
        schema = registry.get_fragment_schema("news_item")
        assert schema is not None
        assert schema.group == "public"

    def test_style_metadata_group_validation(self, test_data_dir, logger):
        """Test that style metadata group matches directory."""
        registry = StyleRegistry(str(test_data_dir / "styles"), logger)
        
        # Get a style and verify its group matches directory
        metadata = registry.get_style_metadata("default")
        assert metadata is not None
        assert metadata.group == "public"


class TestMultiGroupLoading:
    """Test loading multiple groups simultaneously."""

    def test_load_multiple_groups_templates(self, test_data_dir, logger):
        """Test loading templates from multiple groups."""
        # Load with multiple groups (would need additional test fixtures)
        registry = TemplateRegistry(
            str(test_data_dir / "templates"),
            logger,
            groups=["public"]  # Only public exists in test fixtures
        )
        groups = registry.list_groups()
        assert "public" in groups

    def test_load_multiple_groups_fragments(self, test_data_dir, logger):
        """Test loading fragments from multiple groups."""
        registry = FragmentRegistry(
            str(test_data_dir / "fragments"),
            logger,
            groups=["public"]  # Only public exists in test fixtures
        )
        groups = registry.list_groups()
        assert "public" in groups

    def test_load_multiple_groups_styles(self, test_data_dir, logger):
        """Test loading styles from multiple groups."""
        registry = StyleRegistry(
            str(test_data_dir / "styles"),
            logger,
            groups=["public"]  # Only public exists in test fixtures
        )
        groups = registry.list_groups()
        assert "public" in groups


class TestGroupIsolationInSchemas:
    """Test that schemas correctly include group information."""

    def test_template_schema_includes_group(self, test_data_dir, logger):
        """Test that TemplateSchema includes group information."""
        registry = TemplateRegistry(str(test_data_dir / "templates"), logger)
        schema = registry.get_template_schema("basic_report")
        
        assert schema is not None
        assert hasattr(schema.metadata, "group")
        assert schema.metadata.group == "public"

    def test_fragment_schema_includes_group(self, test_data_dir, logger):
        """Test that FragmentSchema includes group information."""
        registry = FragmentRegistry(str(test_data_dir / "fragments"), logger)
        schema = registry.get_fragment_schema("news_item")
        
        assert schema is not None
        assert hasattr(schema, "group")
        assert schema.group == "public"

    def test_style_metadata_includes_group(self, test_data_dir, logger):
        """Test that StyleMetadata includes group information."""
        registry = StyleRegistry(str(test_data_dir / "styles"), logger)
        metadata = registry.get_style_metadata("default")
        
        assert metadata is not None
        assert hasattr(metadata, "group")
        assert metadata.group == "public"

    def test_template_details_includes_group(self, test_data_dir, logger):
        """Test that template details include group."""
        registry = TemplateRegistry(str(test_data_dir / "templates"), logger)
        details = registry.get_template_details("basic_report")
        
        assert details is not None
        assert hasattr(details, "group")
        assert details.group == "public"


class TestEmbeddedFragmentsInheritGroup:
    """Test that fragments embedded in templates inherit template's group."""

    def test_embedded_fragments_get_template_group(self, test_data_dir, logger):
        """Test that embedded fragments inherit template's group."""
        registry = TemplateRegistry(str(test_data_dir / "templates"), logger)
        schema = registry.get_template_schema("basic_report")
        
        assert schema is not None
        assert len(schema.fragments) > 0
        
        # All embedded fragments should have the template's group
        for fragment in schema.fragments:
            assert fragment.group == schema.metadata.group
            assert fragment.group == "public"
