"""Tests for document validation and schema validation functionality"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.validation.document_models import (
    ParameterSchema,
    FragmentSchema,
    TemplateSchema,
    TemplateMetadata,
    DocumentSession,
    FragmentInstance,
)


class TestParameterValidation:
    """Test parameter schema validation"""

    def test_parameter_schema_creation(self):
        """Test creating parameter schemas"""
        param = ParameterSchema(
            name="title",
            type="string",
            description="Document title",
            required=True,
        )

        assert param.name == "title"
        assert param.type == "string"
        assert param.required is True

    def test_parameter_schema_with_default(self):
        """Test parameter schema with default value"""
        param = ParameterSchema(
            name="color",
            type="string",
            description="Text color",
            required=False,
            default="black",
        )

        assert param.default == "black"
        assert param.required is False

    def test_parameter_schema_with_example(self):
        """Test parameter schema with example"""
        param = ParameterSchema(
            name="count",
            type="integer",
            description="Item count",
            example=5,
        )

        assert param.example == 5


class TestFragmentSchemaValidation:
    """Test fragment schema creation and validation"""

    def test_fragment_schema_creation(self):
        """Test creating fragment schemas"""
        fragment = FragmentSchema(
            fragment_id="header",
            group="public",
            name="Header",
            description="Document header",
        )

        assert fragment.fragment_id == "header"
        assert fragment.group == "public"
        assert fragment.name == "Header"

    def test_fragment_schema_with_parameters(self):
        """Test fragment schema with parameters"""
        params = [
            ParameterSchema(
                name="title",
                type="string",
                description="Header title",
            ),
            ParameterSchema(
                name="level",
                type="integer",
                description="Header level",
            ),
        ]

        fragment = FragmentSchema(
            fragment_id="heading",
            group="public",
            name="Heading",
            description="Heading fragment",
            parameters=params,
        )

        assert len(fragment.parameters) == 2
        assert fragment.parameters[0].name == "title"


class TestTemplateSchemaValidation:
    """Test template schema creation and validation"""

    def test_template_metadata_creation(self):
        """Test creating template metadata"""
        metadata = TemplateMetadata(
            template_id="letter",
            group="public",
            name="Letter Template",
            description="Professional letter template",
        )

        assert metadata.template_id == "letter"
        assert metadata.group == "public"
        assert metadata.version == "1.0.0"

    def test_template_schema_creation(self):
        """Test creating complete template schemas"""
        metadata = TemplateMetadata(
            template_id="report",
            group="public",
            name="Report",
            description="Report template",
        )

        schema = TemplateSchema(
            metadata=metadata,
            global_parameters=[],
            fragments=[],
        )

        assert schema.metadata.template_id == "report"
        assert len(schema.fragments) == 0

    def test_template_schema_with_fragments(self):
        """Test template schema with multiple fragments"""
        metadata = TemplateMetadata(
            template_id="article",
            group="public",
            name="Article",
            description="Article template",
        )

        fragments = [
            FragmentSchema(
                fragment_id="intro",
                group="public",
                name="Introduction",
                description="Article introduction",
            ),
            FragmentSchema(
                fragment_id="body",
                group="public",
                name="Body",
                description="Article body",
            ),
            FragmentSchema(
                fragment_id="conclusion",
                group="public",
                name="Conclusion",
                description="Article conclusion",
            ),
        ]

        schema = TemplateSchema(
            metadata=metadata,
            fragments=fragments,
        )

        assert len(schema.fragments) == 3
        assert schema.fragments[0].fragment_id == "intro"


class TestDocumentSessionValidation:
    """Test document session creation and validation"""

    def test_document_session_creation(self):
        """Test creating document sessions"""
        session = DocumentSession(
            session_id="sess-123",
            template_id="letter",
            group="public",
            created_at="2025-11-16T10:00:00",
            updated_at="2025-11-16T10:00:00",
        )

        assert session.session_id == "sess-123"
        assert session.template_id == "letter"
        assert session.group == "public"

    def test_document_session_with_global_parameters(self):
        """Test session with global parameters"""
        session = DocumentSession(
            session_id="sess-456",
            template_id="report",
            group="public",
            global_parameters={"author": "John Doe", "date": "2025-11-16"},
            created_at="2025-11-16T10:00:00",
            updated_at="2025-11-16T10:00:00",
        )

        assert session.global_parameters["author"] == "John Doe"

    def test_document_session_with_fragments(self):
        """Test session with fragment instances"""
        fragments = [
            {"fragment_id": "intro", "parameters": {"text": "Welcome"}},
            {"fragment_id": "body", "parameters": {"content": "Main content"}},
        ]

        session = DocumentSession(
            session_id="sess-789",
            template_id="article",
            group="public",
            fragments=fragments,
            created_at="2025-11-16T10:00:00",
            updated_at="2025-11-16T10:00:00",
        )

        assert len(session.fragments) == 2
        assert isinstance(session.fragments[0], FragmentInstance)

    def test_fragment_instance_conversion(self):
        """Test automatic conversion of dict fragments to FragmentInstance"""
        fragments = [
            {"fragment_id": "header"},
            {"fragment_id": "footer", "parameters": {"page_number": True}},
        ]

        session = DocumentSession(
            session_id="sess-conv",
            template_id="page",
            group="public",
            fragments=fragments,
            created_at="2025-11-16T10:00:00",
            updated_at="2025-11-16T10:00:00",
        )

        assert all(isinstance(f, FragmentInstance) for f in session.fragments)
        assert session.fragments[0].fragment_id == "header"
        assert session.fragments[1].parameters.get("page_number") is True
