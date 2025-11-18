"""Session manager for document generation sessions."""

import uuid
from datetime import datetime
from typing import Dict, Optional

from app.logger import Logger
from app.sessions.storage import SessionStore
from app.templates.registry import TemplateRegistry
from app.validation.document_models import (
    AbortSessionOutput,
    AddFragmentOutput,
    CreateSessionOutput,
    DocumentSession,
    FragmentInstance,
    ListSessionFragmentsOutput,
    RemoveFragmentOutput,
    SessionFragmentInfo,
    SetGlobalParametersOutput,
)


class SessionManager:
    """Manages document generation sessions with persistent storage."""

    def __init__(
        self,
        session_store: SessionStore,
        template_registry: TemplateRegistry,
        logger: Logger,
    ) -> None:
        """
        Initialize the session manager.

        Args:
            session_store: Persistent storage for document sessions
            template_registry: Template registry for validation
            logger: Logger instance
        """
        self.session_store = session_store
        self.template_registry = template_registry
        self.logger = logger

    async def create_session(self, template_id: str, group: str) -> CreateSessionOutput:
        """
        Create a new document session with group-based isolation.

        The session will be bound to the specified group and stored in the
        group-specific directory (data/docs/sessions/{group}/). All subsequent
        operations on this session will verify group ownership.

        Args:
            template_id: Template to use for this session
            group: Group context for this session (determines isolation boundary)

        Returns:
            CreateSessionOutput with session_id

        Raises:
            ValueError: If template doesn't exist
        """
        if not self.template_registry.template_exists(template_id):
            raise ValueError(f"Template '{template_id}' not found")

        session_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        session = DocumentSession(
            session_id=session_id,
            template_id=template_id,
            group=group,
            global_parameters=None,
            fragments=[],
            created_at=now,
            updated_at=now,
        )

        # Persist session
        await self.session_store.save_session(session)

        self.logger.info(f"Created session {session_id} with template {template_id}")

        return CreateSessionOutput(session_id=session_id, template_id=template_id, created_at=now)

    async def get_session(self, session_id: str) -> Optional[DocumentSession]:
        """
        Retrieve a session from storage.

        Args:
            session_id: Session to retrieve

        Returns:
            DocumentSession or None if not found
        """
        return await self.session_store.load_session(session_id)

    async def set_global_parameters(
        self, session_id: str, parameters: Dict
    ) -> SetGlobalParametersOutput:
        """
        Set global parameters for a session.

        Args:
            session_id: Session to update
            parameters: Global parameters

        Returns:
            SetGlobalParametersOutput

        Raises:
            ValueError: If session not found or validation fails
        """
        session = await self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session '{session_id}' not found")

        # Validate parameters
        is_valid, errors = self.template_registry.validate_global_parameters(
            session.template_id, parameters
        )
        if not is_valid:
            raise ValueError(f"Invalid global parameters: {'; '.join(errors)}")

        # Update session
        session.global_parameters = parameters
        session.updated_at = datetime.utcnow().isoformat()

        await self.session_store.save_session(session)

        self.logger.info(f"Set global parameters for session {session_id}")

        return SetGlobalParametersOutput(
            session_id=session_id,
            message="Global parameters set successfully",
        )

    async def add_fragment(
        self, session_id: str, fragment_id: str, parameters: Dict, position: str = "end"
    ) -> AddFragmentOutput:
        """
        Add a fragment to a session.

        Args:
            session_id: Session to update
            fragment_id: Fragment type to add
            parameters: Fragment parameters
            position: Where to add ('start', 'end', 'before:<guid>', 'after:<guid>')

        Returns:
            AddFragmentOutput with fragment_instance_guid

        Raises:
            ValueError: If session not found, validation fails, or position is invalid
        """
        session = await self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session '{session_id}' not found")

        # Validate fragment parameters
        is_valid, errors = self.template_registry.validate_fragment_parameters(
            session.template_id, fragment_id, parameters
        )
        if not is_valid:
            raise ValueError(f"Invalid fragment parameters: {'; '.join(errors)}")

        # Create fragment instance
        fragment_instance_guid = str(uuid.uuid4())
        fragment_instance = FragmentInstance(
            fragment_id=fragment_id,
            parameters=parameters,
            fragment_instance_guid=fragment_instance_guid,
            created_at=datetime.utcnow().isoformat(),
        )

        # Determine insertion position
        insert_index = self._calculate_insert_index(session, position)

        # Insert fragment
        session.fragments.insert(insert_index, fragment_instance)
        session.updated_at = datetime.utcnow().isoformat()

        await self.session_store.save_session(session)

        self.logger.info(
            f"Added fragment {fragment_id} (instance {fragment_instance_guid}) "
            f"to session {session_id} at position {insert_index}"
        )

        return AddFragmentOutput(
            session_id=session_id,
            fragment_instance_guid=fragment_instance_guid,
            fragment_id=fragment_id,
            position=insert_index,
            message=f"Fragment added successfully at position {insert_index}",
        )

    def _calculate_insert_index(self, session: DocumentSession, position: str) -> int:
        """
        Calculate where to insert a fragment.

        Args:
            session: Document session
            position: Position specification

        Returns:
            Insert index

        Raises:
            ValueError: If position is invalid or reference GUID not found
        """
        if position == "start":
            return 0
        elif position == "end":
            return len(session.fragments)
        elif position.startswith("before:"):
            guid = position[7:]
            for idx, frag in enumerate(session.fragments):
                if frag.fragment_instance_guid == guid:
                    return idx
            raise ValueError(f"Fragment instance '{guid}' not found in session")
        elif position.startswith("after:"):
            guid = position[6:]
            for idx, frag in enumerate(session.fragments):
                if frag.fragment_instance_guid == guid:
                    return idx + 1
            raise ValueError(f"Fragment instance '{guid}' not found in session")
        else:
            raise ValueError(
                f"Invalid position '{position}'. "
                f"Expected 'start', 'end', 'before:<guid>', or 'after:<guid>'"
            )

    async def remove_fragment(
        self, session_id: str, fragment_instance_guid: str
    ) -> RemoveFragmentOutput:
        """
        Remove a fragment from a session.

        Args:
            session_id: Session to update
            fragment_instance_guid: Fragment instance to remove

        Returns:
            RemoveFragmentOutput

        Raises:
            ValueError: If session or fragment not found
        """
        session = await self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session '{session_id}' not found")

        # Find and remove fragment
        original_length = len(session.fragments)
        session.fragments = [
            f for f in session.fragments if f.fragment_instance_guid != fragment_instance_guid
        ]

        if len(session.fragments) == original_length:
            raise ValueError(f"Fragment instance '{fragment_instance_guid}' not found in session")

        session.updated_at = datetime.utcnow().isoformat()

        await self.session_store.save_session(session)

        self.logger.info(
            f"Removed fragment instance {fragment_instance_guid} from session {session_id}"
        )

        return RemoveFragmentOutput(
            session_id=session_id,
            fragment_instance_guid=fragment_instance_guid,
            message="Fragment removed successfully",
        )

    async def list_session_fragments(self, session_id: str) -> ListSessionFragmentsOutput:
        """
        List all fragments in a session.

        Args:
            session_id: Session to query

        Returns:
            ListSessionFragmentsOutput

        Raises:
            ValueError: If session not found
        """
        session = await self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session '{session_id}' not found")

        fragment_infos = []
        for idx, fragment_instance in enumerate(session.fragments):
            # Get fragment name from template
            fragment_schema = self.template_registry.get_fragment_schema(
                session.template_id, fragment_instance.fragment_id
            )
            fragment_name = fragment_schema.name if fragment_schema else "Unknown"

            fragment_infos.append(
                SessionFragmentInfo(
                    fragment_instance_guid=fragment_instance.fragment_instance_guid,
                    fragment_id=fragment_instance.fragment_id,
                    fragment_name=fragment_name,
                    position=idx,
                    parameters=fragment_instance.parameters,
                )
            )

        return ListSessionFragmentsOutput(
            session_id=session_id,
            fragment_count=len(fragment_infos),
            fragments=fragment_infos,
        )

    async def abort_session(self, session_id: str) -> AbortSessionOutput:
        """
        Delete a session and all its data.

        Args:
            session_id: Session to delete

        Returns:
            AbortSessionOutput

        Raises:
            ValueError: If session not found
        """
        session = await self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session '{session_id}' not found")

        await self.session_store.delete_session(session_id)

        self.logger.info(f"Aborted session {session_id}")

        return AbortSessionOutput(
            session_id=session_id,
            message="Session terminated and all data deleted",
        )

    async def validate_session_for_render(self, session_id: str) -> tuple[bool, Optional[str]]:
        """
        Validate that a session is ready for rendering.

        Args:
            session_id: Session to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        session = await self.get_session(session_id)
        if session is None:
            return False, f"Session '{session_id}' not found"

        if session.global_parameters is None:
            return False, (
                "Global parameters not set. " "Call set_global_parameters before rendering."
            )

        return True, None

    async def get_session_status(self, session_id: str):
        """
        Get current status of a session.

        Note: This method returns session information without group filtering.
        The caller (MCP tool handler) is responsible for verifying that the
        session belongs to the authenticated user's group before calling this method.

        Args:
            session_id: Session to check

        Returns:
            SessionStatusOutput with current state including group field

        Raises:
            ValueError: If session not found
        """
        from app.validation.document_models import SessionStatusOutput

        session = await self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session '{session_id}' not found")

        has_globals = session.global_parameters is not None and len(session.global_parameters) > 0
        is_ready, _ = await self.validate_session_for_render(session_id)

        return SessionStatusOutput(
            session_id=session.session_id,
            template_id=session.template_id,
            group=session.group,
            has_global_parameters=has_globals,
            fragment_count=len(session.fragments),
            is_ready_to_render=is_ready,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message=f"Session '{session_id}' status retrieved successfully",
        )

    async def list_active_sessions(self):
        """
        List all active sessions with summary information.

        Note: This method returns ALL sessions across all groups. The caller
        (MCP tool handler) is responsible for filtering sessions by the
        authenticated user's group before returning results to the client.

        Returns:
            ListActiveSessionsOutput with session summaries (includes group field for filtering)
        """
        from app.validation.document_models import ListActiveSessionsOutput, SessionSummary

        session_ids = await self.session_store.list_sessions()
        summaries = []

        for session_id in session_ids:
            session = await self.get_session(session_id)
            if session:
                has_globals = (
                    session.global_parameters is not None and len(session.global_parameters) > 0
                )
                summaries.append(
                    SessionSummary(
                        session_id=session.session_id,
                        template_id=session.template_id,
                        group=session.group,
                        fragment_count=len(session.fragments),
                        has_global_parameters=has_globals,
                        created_at=session.created_at,
                        updated_at=session.updated_at,
                    )
                )

        self.logger.info(f"Listed {len(summaries)} active sessions")

        return ListActiveSessionsOutput(
            session_count=len(summaries),
            sessions=summaries,
        )

    async def validate_parameters(
        self,
        template_id: str,
        parameters: Dict,
        parameter_type: str = "global",
        fragment_id: Optional[str] = None,
    ):
        """
        Validate parameters without saving them.

        Note: This method validates parameters without group filtering. The caller
        (MCP tool handler) is responsible for verifying that the template or fragment
        belongs to the authenticated user's group before calling this method.

        Args:
            template_id: Template to validate against
            parameters: Parameters to validate
            parameter_type: 'global' or 'fragment'
            fragment_id: Required if parameter_type is 'fragment'

        Returns:
            ValidateParametersOutput with detailed validation results

        Raises:
            ValueError: If template or fragment not found
        """
        from app.validation.document_models import ValidateParametersOutput, ValidationError

        if not self.template_registry.template_exists(template_id):
            raise ValueError(f"Template '{template_id}' not found")

        if parameter_type == "global":
            is_valid, error_messages = self.template_registry.validate_global_parameters(
                template_id, parameters
            )

            # Convert simple error messages to ValidationError objects with enhanced info
            errors = []
            if not is_valid:
                # Get parameter schemas for enhanced error details
                template_schema = self.template_registry.get_template_schema(template_id)
                param_schemas = {p.name: p for p in template_schema.global_parameters}

                for error_msg in error_messages:
                    # Try to extract parameter name from error message
                    param_name = error_msg.split("'")[1] if "'" in error_msg else "unknown"
                    param_schema = param_schemas.get(param_name)

                    errors.append(
                        ValidationError(
                            parameter=param_name,
                            error=error_msg,
                            expected_type=param_schema.type if param_schema else None,
                            received_type=(
                                type(parameters.get(param_name)).__name__
                                if param_name in parameters
                                else None
                            ),
                            example=param_schema.example if param_schema else None,
                        )
                    )

            return ValidateParametersOutput(
                is_valid=is_valid,
                parameter_type="global",
                template_id=template_id,
                errors=errors,
                message=(
                    "Parameters valid" if is_valid else f"Found {len(errors)} validation errors"
                ),
            )

        elif parameter_type == "fragment":
            if not fragment_id:
                raise ValueError("fragment_id required when parameter_type is 'fragment'")

            is_valid, error_messages = self.template_registry.validate_fragment_parameters(
                template_id, fragment_id, parameters
            )

            # Convert simple error messages to ValidationError objects
            errors = []
            if not is_valid:
                fragment_schema = self.template_registry.get_fragment_schema(
                    template_id, fragment_id
                )
                param_schemas = (
                    {p.name: p for p in fragment_schema.parameters} if fragment_schema else {}
                )

                for error_msg in error_messages:
                    param_name = error_msg.split("'")[1] if "'" in error_msg else "unknown"
                    param_schema = param_schemas.get(param_name)

                    errors.append(
                        ValidationError(
                            parameter=param_name,
                            error=error_msg,
                            expected_type=param_schema.type if param_schema else None,
                            received_type=(
                                type(parameters.get(param_name)).__name__
                                if param_name in parameters
                                else None
                            ),
                            example=param_schema.example if param_schema else None,
                        )
                    )

            return ValidateParametersOutput(
                is_valid=is_valid,
                parameter_type="fragment",
                template_id=template_id,
                fragment_id=fragment_id,
                errors=errors,
                message=(
                    "Parameters valid" if is_valid else f"Found {len(errors)} validation errors"
                ),
            )
        else:
            raise ValueError(
                f"Invalid parameter_type '{parameter_type}'. Must be 'global' or 'fragment'"
            )
