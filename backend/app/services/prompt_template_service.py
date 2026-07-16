"""
Prompt Template Service.

Dedicated service layer for prompt template CRUD operations.
Wraps the PromptTemplateRepository and enforces business rules:
 - System default templates cannot be modified or deleted.
 - Template names are globally unique.
 - Only custom templates may be updated/deleted.
"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt_template import PromptTemplate
from app.repositories.prompt_template import PromptTemplateRepository


class PromptTemplateService:
    """
    Service layer for prompt template management.

    Enforces invariants that belong in the service layer rather than at the
    HTTP routing layer, so the business rules remain testable independently
    of FastAPI.
    """

    def __init__(
        self,
        session: AsyncSession,
        template_repo: PromptTemplateRepository | None = None,
    ) -> None:
        self._session = session
        self._repo = template_repo or PromptTemplateRepository(session)

    async def get_all_templates(self, *, limit: int = 1000) -> list[PromptTemplate]:
        """Return all prompt templates (system defaults + custom)."""
        return await self._repo.get_all(limit=limit)

    async def get_by_id(self, template_id: UUID) -> PromptTemplate | None:
        """Fetch a single template by UUID primary key."""
        return await self._repo.get_by_id(template_id)

    async def get_by_generation_type(self, generation_type: str) -> PromptTemplate | None:
        """
        Fetch the preferred template for a generation type.
        Custom templates take priority over system defaults.
        """
        return await self._repo.get_by_generation_type(generation_type)

    async def create_custom_template(
        self,
        name: str,
        generation_type: str,
        system_prompt: str,
        instruction_prompt: str,
        educational_constraints: str,
        output_format: str,
    ) -> PromptTemplate:
        """
        Create a new custom (non-system-default) prompt template.

        :raises ValueError: If a template with the same name already exists.
        """
        existing = await self._repo.get_by_name(name)
        if existing:
            raise ValueError(f"A prompt template named '{name}' already exists.")

        template = PromptTemplate(
            name=name,
            generation_type=generation_type,
            system_prompt=system_prompt,
            instruction_prompt=instruction_prompt,
            educational_constraints=educational_constraints,
            output_format=output_format,
            is_system_default=False,
        )
        return await self._repo.create(template)

    async def update_custom_template(
        self,
        template_id: UUID,
        update_data: dict,
    ) -> PromptTemplate:
        """
        Update a custom template.

        :raises ValueError: If the template does not exist, or if it is a
            system default, or if the requested new name is already taken.
        """
        template = await self._repo.get_by_id(template_id)
        if not template:
            raise ValueError(f"Prompt template with ID '{template_id}' not found.")
        if template.is_system_default:
            raise ValueError("System default templates cannot be modified.")

        # Name-uniqueness check when renaming
        new_name = update_data.get("name")
        if new_name is not None:
            conflicting = await self._repo.get_by_name(new_name)
            if conflicting and conflicting.id != template_id:
                raise ValueError(f"A prompt template named '{new_name}' already exists.")

        return await self._repo.update(template, update_data)

    async def delete_custom_template(self, template_id: UUID) -> None:
        """
        Delete a custom template.

        :raises ValueError: If the template does not exist or is a system default.
        """
        template = await self._repo.get_by_id(template_id)
        if not template:
            raise ValueError(f"Prompt template with ID '{template_id}' not found.")
        if template.is_system_default:
            raise ValueError("System default templates cannot be deleted.")

        await self._repo.delete(template)
