#!/usr/bin/env python3
"""Render Manager CLI

Command-line utility to manage document rendering including template and fragment discovery,
parameter validation, and template/fragment inspection.
"""

import argparse
import sys
import os
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.templates.registry import TemplateRegistry
from app.fragments.registry import FragmentRegistry
from app.styles.registry import StyleRegistry
from app.logger import Logger, session_logger


def resolve_templates_dir(cli_dir: Optional[str], data_root: Optional[str] = None) -> str:
    """
    Resolve templates directory with priority chain.

    Priority:
    1. CLI --data-root argument (docs/templates subdirectory)
    2. CLI --templates-dir argument (legacy)
    3. DOCO_DATA environment variable
    4. Project default
    """
    # Priority 1: --data-root points to data directory, docs/templates is subdirectory
    if data_root:
        return str(Path(data_root) / "docs" / "templates")

    # Priority 2: Legacy --templates-dir argument
    if cli_dir:
        return cli_dir

    # Priority 3: DOCO_DATA environment variable
    doco_data = os.environ.get("DOCO_DATA")
    if doco_data:
        return str(Path(doco_data) / "docs" / "templates")

    # Priority 4: Project default
    project_root = Path(__file__).parent.parent.parent
    return str(project_root / "data" / "docs" / "templates")


def resolve_fragments_dir(cli_dir: Optional[str], data_root: Optional[str] = None) -> str:
    """
    Resolve fragments directory with priority chain.

    Priority:
    1. CLI --data-root argument (docs/fragments subdirectory)
    2. CLI --fragments-dir argument (legacy)
    3. DOCO_DATA environment variable
    4. Project default
    """
    # Priority 1: --data-root points to data directory, docs/fragments is subdirectory
    if data_root:
        return str(Path(data_root) / "docs" / "fragments")

    # Priority 2: Legacy --fragments-dir argument
    if cli_dir:
        return cli_dir

    # Priority 3: DOCO_DATA environment variable
    doco_data = os.environ.get("DOCO_DATA")
    if doco_data:
        return str(Path(doco_data) / "docs" / "fragments")

    # Priority 4: Project default
    project_root = Path(__file__).parent.parent.parent
    return str(project_root / "data" / "docs" / "fragments")


def resolve_styles_dir(cli_dir: Optional[str], data_root: Optional[str] = None) -> str:
    """
    Resolve styles directory with priority chain.

    Priority:
    1. CLI --data-root argument (docs/styles subdirectory)
    2. CLI --styles-dir argument (legacy)
    3. DOCO_DATA environment variable
    4. Project default
    """
    # Priority 1: --data-root points to data directory, docs/styles is subdirectory
    if data_root:
        return str(Path(data_root) / "docs" / "styles")

    # Priority 2: Legacy --styles-dir argument
    if cli_dir:
        return cli_dir

    # Priority 3: DOCO_DATA environment variable
    doco_data = os.environ.get("DOCO_DATA")
    if doco_data:
        return str(Path(doco_data) / "docs" / "styles")

    # Priority 4: Project default
    project_root = Path(__file__).parent.parent.parent
    return str(project_root / "data" / "docs" / "styles")


def list_templates(args):
    """List all available templates"""
    logger: Logger = session_logger

    templates_dir = resolve_templates_dir(args.templates_dir, args.data_root)

    try:
        registry = TemplateRegistry(templates_dir, logger)
        templates = registry.list_templates(group=args.group)

        if not templates:
            group_msg = f" in group '{args.group}'" if args.group else ""
            logger.info(f"No templates found{group_msg}.")
            return 0

        group_msg = f" in group '{args.group}'" if args.group else ""
        logger.info(f"{len(templates)} Template(s) Found{group_msg}:")

        if args.verbose:
            if args.group:
                logger.info(f"{'Template ID':<25} {'Name':<30} {'Group':<15} {'Description'}")
                logger.info("-" * 115)
                for tmpl in templates:
                    logger.info(
                        f"{tmpl.template_id:<25} {tmpl.name:<30} {tmpl.group:<15} {tmpl.description}"
                    )
            else:
                logger.info(f"{'Template ID':<25} {'Group':<15} {'Name':<30} {'Description'}")
                logger.info("-" * 115)
                for tmpl in templates:
                    logger.info(
                        f"{tmpl.template_id:<25} {tmpl.group:<15} {tmpl.name:<30} {tmpl.description}"
                    )
        else:
            for tmpl in templates:
                group_label = f" [{tmpl.group}]" if not args.group else ""
                logger.info(f"{tmpl.template_id}{group_label}")

        return 0

    except Exception as e:
        logger.error(f"Error listing templates: {str(e)}")
        return 1


def get_template_details(args):
    """Get detailed information about a template"""
    logger: Logger = session_logger

    templates_dir = resolve_templates_dir(args.templates_dir, args.data_root)

    try:
        registry = TemplateRegistry(templates_dir, logger)

        if not registry.template_exists(args.template_id):
            logger.error(f"Template '{args.template_id}' not found")
            return 1

        details = registry.get_template_details(args.template_id)

        if not details:
            logger.error(f"Could not retrieve details for template '{args.template_id}'")
            return 1

        logger.info(f"Template: {details.template_id}")
        logger.info(f"Name: {details.name}")
        logger.info(f"Description: {details.description}")

        # Get the full schema to access parameter details properly
        schema = registry.get_template_schema(args.template_id)
        if schema and schema.global_parameters:
            logger.info("\nGlobal Parameters:")
            for param in schema.global_parameters:
                required_str = "required" if param.required else "optional"
                logger.info(f"  - {param.name} ({param.type}) [{required_str}]")
                if param.description:
                    logger.info(f"    {param.description}")
                if param.default is not None:
                    logger.info(f"    Default: {param.default}")
        else:
            logger.info("No global parameters")

        return 0

    except Exception as e:
        logger.error(f"Error getting template details: {str(e)}")
        return 1


def list_template_fragments(args):
    """List fragments available in a template"""
    logger: Logger = session_logger

    templates_dir = resolve_templates_dir(args.templates_dir, args.data_root)

    try:
        registry = TemplateRegistry(templates_dir, logger)

        if not registry.template_exists(args.template_id):
            logger.error(f"Template '{args.template_id}' not found")
            return 1

        schema = registry.get_template_schema(args.template_id)
        fragments = schema.fragments if schema else []

        if not fragments:
            logger.info(f"Template '{args.template_id}' has no fragments")
            return 0

        logger.info(f"{len(fragments)} Fragment(s) in template '{args.template_id}':")

        if args.verbose:
            logger.info(f"{'Fragment ID':<25} {'Name':<30} {'Description':<40} {'Params'}")
            logger.info("-" * 120)
            for frag in fragments:
                params_count = len(frag.parameters)
                logger.info(
                    f"{frag.fragment_id:<25} {frag.name:<30} {frag.description:<40} {params_count}"
                )
        else:
            for frag in fragments:
                logger.info(frag.fragment_id)

        return 0

    except Exception as e:
        logger.error(f"Error listing fragments: {str(e)}")
        return 1


def get_fragment_details(args):
    """Get detailed information about a fragment in a template"""
    logger: Logger = session_logger

    templates_dir = resolve_templates_dir(args.templates_dir, args.data_root)

    try:
        registry = TemplateRegistry(templates_dir, logger)

        # template_id comes from positional argument in "templates fragments <template_id>"
        template_id = getattr(args, "template_id", None)
        if not template_id:
            logger.error("Template ID is required")
            return 1

        if not registry.template_exists(template_id):
            logger.error(f"Template '{template_id}' not found")
            return 1

        # fragment_id comes from --fragment flag
        fragment_id = getattr(args, "fragment", None)
        if not fragment_id:
            logger.error("Fragment ID is required (use --fragment)")
            return 1

        fragment = registry.get_fragment_schema(template_id, fragment_id)

        if not fragment:
            logger.error(f"Fragment '{fragment_id}' not found in template '{template_id}'")
            return 1

        logger.info(f"Fragment: {fragment.fragment_id}")
        logger.info(f"Template: {template_id}")
        logger.info(f"Name: {fragment.name}")
        logger.info(f"Description: {fragment.description}")

        if fragment.parameters:
            logger.info("\nParameters:")
            for param in fragment.parameters:
                required = "required" if param.required else "optional"
                logger.info(f"  - {param.name} ({param.type}) [{required}]")
                if param.description:
                    logger.info(f"    {param.description}")
                if param.default is not None:
                    logger.info(f"    Default: {param.default}")
        else:
            logger.info("No parameters")

        return 0

    except Exception as e:
        logger.error(f"Error getting fragment details: {str(e)}")
        return 1


def list_standalone_fragments(args):
    """List all standalone fragments"""
    logger: Logger = session_logger

    fragments_dir = resolve_fragments_dir(args.fragments_dir, args.data_root)

    try:
        registry = FragmentRegistry(fragments_dir, logger)
        fragments = registry.list_fragments(group=args.group)

        if not fragments:
            group_msg = f" in group '{args.group}'" if args.group else ""
            logger.info(f"No standalone fragments found{group_msg}.")
            return 0

        group_msg = f" in group '{args.group}'" if args.group else ""
        logger.info(f"{len(fragments)} Standalone Fragment(s) Found{group_msg}:")

        if args.verbose:
            if args.group:
                logger.info(
                    f"{'Fragment ID':<25} {'Name':<30} {'Group':<15} {'Description':<40} {'Params'}"
                )
                logger.info("-" * 130)
                for frag in fragments:
                    logger.info(
                        f"{frag['fragment_id']:<25} {frag['name']:<30} {frag['group']:<15} {frag['description']:<40} {frag['parameter_count']}"
                    )
            else:
                logger.info(
                    f"{'Fragment ID':<25} {'Group':<15} {'Name':<30} {'Description':<40} {'Params'}"
                )
                logger.info("-" * 130)
                for frag in fragments:
                    logger.info(
                        f"{frag['fragment_id']:<25} {frag['group']:<15} {frag['name']:<30} {frag['description']:<40} {frag['parameter_count']}"
                    )
        else:
            for frag in fragments:
                group_label = f" [{frag['group']}]" if not args.group else ""
                logger.info(f"{frag['fragment_id']}{group_label}")

        return 0

    except Exception as e:
        logger.error(f"Error listing standalone fragments: {str(e)}")
        return 1


def get_standalone_fragment_details(args):
    """Get detailed information about a standalone fragment"""
    logger: Logger = session_logger

    fragments_dir = resolve_fragments_dir(args.fragments_dir, args.data_root)

    try:
        registry = FragmentRegistry(fragments_dir, logger)

        if not registry.fragment_exists(args.fragment_id):
            logger.error(f"Fragment '{args.fragment_id}' not found")
            return 1

        schema = registry.get_fragment_schema(args.fragment_id)

        if not schema:
            logger.error(f"Could not retrieve schema for fragment '{args.fragment_id}'")
            return 1

        logger.info(f"Fragment: {schema.fragment_id}")
        logger.info(f"Name: {schema.name}")
        logger.info(f"Description: {schema.description}")

        if schema.parameters:
            logger.info("\nParameters:")
            for param in schema.parameters:
                required = "required" if param.required else "optional"
                logger.info(f"  - {param.name} ({param.type}) [{required}]")
                if param.description:
                    logger.info(f"    {param.description}")
                if param.default is not None:
                    logger.info(f"    Default: {param.default}")
        else:
            logger.info("No parameters")

        return 0

    except Exception as e:
        logger.error(f"Error getting fragment details: {str(e)}")
        return 1


def validate_template_parameters(args):
    """Validate parameters against a template's global parameters"""
    logger: Logger = session_logger

    templates_dir = resolve_templates_dir(args.templates_dir, args.data_root)

    try:
        # Parse parameters as JSON or key=value pairs
        params = {}
        if args.parameters:
            for param_str in args.parameters:
                if "=" in param_str:
                    key, value = param_str.split("=", 1)
                    params[key] = value
                else:
                    logger.error(f"Invalid parameter format: {param_str}. Use key=value")
                    return 1

        registry = TemplateRegistry(templates_dir, logger)

        if not registry.template_exists(args.template_id):
            logger.error(f"Template '{args.template_id}' not found")
            return 1

        is_valid, errors = registry.validate_global_parameters(args.template_id, params)

        if is_valid:
            logger.info(f"✓ Template '{args.template_id}' parameters are valid")
            if params:
                logger.info("Provided parameters:")
                for key, value in params.items():
                    logger.info(f"  {key}: {value}")
            return 0
        else:
            logger.error(f"✗ Template '{args.template_id}' parameters are invalid:")
            for error in errors:
                logger.error(f"  - {error}")
            return 1

    except Exception as e:
        logger.error(f"Error validating parameters: {str(e)}")
        return 1


def list_groups(args):
    """List all available groups"""
    logger: Logger = session_logger

    templates_dir = resolve_templates_dir(args.templates_dir, args.data_root)
    fragments_dir = resolve_fragments_dir(args.fragments_dir, args.data_root)
    styles_dir = resolve_styles_dir(args.styles_dir, args.data_root)

    try:
        # Get groups from all registries
        template_groups = set()
        fragment_groups = set()
        style_groups = set()

        try:
            registry = TemplateRegistry(templates_dir, logger)
            template_groups = set(registry.list_groups())
        except Exception:
            pass

        try:
            registry = FragmentRegistry(fragments_dir, logger)
            fragment_groups = set(registry.list_groups())
        except Exception:
            pass

        try:
            registry = StyleRegistry(styles_dir, logger)
            style_groups = set(registry.list_groups())
        except Exception:
            pass

        # Combine all groups
        all_groups = sorted(template_groups | fragment_groups | style_groups)

        if not all_groups:
            logger.info("No groups found.")
            return 0

        logger.info(f"{len(all_groups)} Group(s) Found:")

        if args.verbose:
            logger.info(f"{'Group':<20} {'Templates':<12} {'Fragments':<12} {'Styles'}")
            logger.info("-" * 60)
            for group in all_groups:
                t_count = len(template_groups & {group})
                f_count = len(fragment_groups & {group})
                s_count = len(style_groups & {group})
                logger.info(f"{group:<20} {t_count:<12} {f_count:<12} {s_count}")
        else:
            for group in all_groups:
                logger.info(group)

        return 0

    except Exception as e:
        logger.error(f"Error listing groups: {str(e)}")
        return 1


def validate_fragment_parameters(args):
    """Validate parameters against a fragment's parameters"""
    logger: Logger = session_logger

    templates_dir = resolve_templates_dir(args.templates_dir, args.data_root)
    fragments_dir = resolve_fragments_dir(args.fragments_dir, args.data_root)

    try:
        # Parse parameters as JSON or key=value pairs
        params = {}
        if args.parameters:
            for param_str in args.parameters:
                if "=" in param_str:
                    key, value = param_str.split("=", 1)
                    params[key] = value
                else:
                    logger.error(f"Invalid parameter format: {param_str}. Use key=value")
                    return 1

        # Try template fragment first
        if args.template_id:
            registry = TemplateRegistry(templates_dir, logger)

            if not registry.template_exists(args.template_id):
                logger.error(f"Template '{args.template_id}' not found")
                return 1

            is_valid, errors = registry.validate_fragment_parameters(
                args.template_id, args.fragment_id, params
            )
            location = f"in template '{args.template_id}'"
        else:
            # Use standalone fragment
            registry = FragmentRegistry(fragments_dir, logger)

            if not registry.fragment_exists(args.fragment_id):
                logger.error(f"Fragment '{args.fragment_id}' not found")
                return 1

            is_valid, errors = registry.validate_parameters(args.fragment_id, params)
            location = "(standalone)"

        if is_valid:
            logger.info(f"✓ Fragment '{args.fragment_id}' {location} parameters are valid")
            if params:
                logger.info("Provided parameters:")
                for key, value in params.items():
                    logger.info(f"  {key}: {value}")
            return 0
        else:
            logger.error(f"✗ Fragment '{args.fragment_id}' {location} parameters are invalid:")
            for error in errors:
                logger.error(f"  - {error}")
            return 1

    except Exception as e:
        logger.error(f"Error validating fragment parameters: {str(e)}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="doco Render Manager - Manage templates and fragments for document rendering",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all groups
  python -m app.management.render_manager groups
  python -m app.management.render_manager groups -v

  # List all templates
  python -m app.management.render_manager templates list
  python -m app.management.render_manager templates list --group public

  # Get template details
  python -m app.management.render_manager templates info basic_report

  # List fragments in a template
  python -m app.management.render_manager templates fragments basic_report

  # Get fragment details from template
  python -m app.management.render_manager templates fragments basic_report --fragment paragraph

  # List standalone fragments
  python -m app.management.render_manager fragments list
  python -m app.management.render_manager fragments list --group public

  # Get standalone fragment details
  python -m app.management.render_manager fragments info news_item

  # Validate template global parameters
  python -m app.management.render_manager validate-template basic_report title="My Report" author="John Doe"

  # Validate fragment parameters in a template
  python -m app.management.render_manager validate-fragment basic_report paragraph text="Hello world"

  # Validate standalone fragment parameters
  python -m app.management.render_manager validate-fragment news_item --standalone headline="Breaking News" body="Story content"

  # Use with environment variables
  python -m app.management.render_manager --doco-env PROD --data-root /path/to/data templates list
  python -m app.management.render_manager --doco-env TEST fragments list

Environment Variables:
    DOCO_ENV            Environment mode (TEST or PROD)
    DOCO_DATA           Data root directory (contains docs/)
        """,
    )

    # Global arguments
    parser.add_argument(
        "--doco-env",
        type=str,
        default=os.environ.get("DOCO_ENV", "TEST"),
        choices=["TEST", "PROD"],
        help="Environment mode (TEST or PROD, default: from DOCO_ENV or TEST)",
    )
    parser.add_argument(
        "--data-root",
        type=str,
        default=os.environ.get("DOCO_DATA"),
        help="Data root directory (contains docs/ with templates, fragments, styles)",
    )

    # Legacy arguments (kept for backward compatibility)
    parser.add_argument(
        "--templates-dir",
        type=str,
        default=None,
        help="Templates directory (default: project data/docs/templates)",
    )
    parser.add_argument(
        "--fragments-dir",
        type=str,
        default=None,
        help="Fragments directory (default: {project}/fragments)",
    )
    parser.add_argument(
        "--styles-dir",
        type=str,
        default=None,
        help="Styles directory (default: {project}/styles)",
    )
    parser.add_argument(
        "--group",
        type=str,
        default=None,
        help="Filter by group (optional)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Groups subcommand
    groups_parser = subparsers.add_parser(
        "groups",
        help="List available groups",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="List all groups across templates, fragments, and styles",
    )
    groups_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed information"
    )

    # Templates subcommand
    templates_parser = subparsers.add_parser(
        "templates",
        help="Manage templates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Template management commands",
    )
    templates_subparsers = templates_parser.add_subparsers(
        dest="templates_cmd", help="Template command"
    )

    # templates list
    templates_list = templates_subparsers.add_parser("list", help="List all templates")
    templates_list.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed information"
    )
    templates_list.add_argument(
        "--group", type=str, default=None, help="Filter by group (optional)"
    )

    # templates info
    templates_info = templates_subparsers.add_parser("info", help="Get template details")
    templates_info.add_argument("template_id", help="Template ID")

    # templates fragments
    templates_frags = templates_subparsers.add_parser("fragments", help="List template fragments")
    templates_frags.add_argument("template_id", help="Template ID")
    templates_frags.add_argument(
        "--fragment", type=str, default=None, help="Get details for a specific fragment"
    )
    templates_frags.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed information"
    )

    # Fragments subcommand
    fragments_parser = subparsers.add_parser(
        "fragments",
        help="Manage standalone fragments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Standalone fragment management commands",
    )
    fragments_subparsers = fragments_parser.add_subparsers(
        dest="fragments_cmd", help="Fragment command"
    )

    # fragments list
    fragments_list = fragments_subparsers.add_parser("list", help="List all standalone fragments")
    fragments_list.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed information"
    )
    fragments_list.add_argument(
        "--group", type=str, default=None, help="Filter by group (optional)"
    )

    # fragments info
    fragments_info = fragments_subparsers.add_parser("info", help="Get fragment details")
    fragments_info.add_argument("fragment_id", help="Fragment ID")

    # Validate template parameters
    validate_tmpl = subparsers.add_parser(
        "validate-template",
        help="Validate template parameters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Validate parameters against template global parameters",
    )
    validate_tmpl.add_argument("template_id", help="Template ID")
    validate_tmpl.add_argument("parameters", nargs="*", help="Parameters as key=value pairs")

    # Validate fragment parameters
    validate_frag = subparsers.add_parser(
        "validate-fragment",
        help="Validate fragment parameters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Validate parameters against fragment parameters",
    )
    validate_frag.add_argument("fragment_id", help="Fragment ID")
    validate_frag.add_argument("parameters", nargs="*", help="Parameters as key=value pairs")
    validate_frag.add_argument(
        "--template", type=str, default=None, help="Template ID (if fragment is in a template)"
    )
    validate_frag.add_argument(
        "--standalone",
        action="store_true",
        help="Validate as standalone fragment (opposite of --template)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    if args.command == "groups":
        return list_groups(args)

    elif args.command == "templates":
        if not args.templates_cmd:
            templates_parser.print_help()
            return 1

        if args.templates_cmd == "list":
            return list_templates(args)
        elif args.templates_cmd == "info":
            return get_template_details(args)
        elif args.templates_cmd == "fragments":
            if args.fragment:
                return get_fragment_details(args)
            else:
                return list_template_fragments(args)

    elif args.command == "fragments":
        if not args.fragments_cmd:
            fragments_parser.print_help()
            return 1

        if args.fragments_cmd == "list":
            return list_standalone_fragments(args)
        elif args.fragments_cmd == "info":
            return get_standalone_fragment_details(args)

    elif args.command == "validate-template":
        return validate_template_parameters(args)

    elif args.command == "validate-fragment":
        args.template_id = args.template
        return validate_fragment_parameters(args)

    else:
        logger: Logger = session_logger
        logger.error(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
