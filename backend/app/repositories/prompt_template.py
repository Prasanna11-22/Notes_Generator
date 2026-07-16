"""
PromptTemplate database repository.
"""

from sqlalchemy import select
from app.models.prompt_template import PromptTemplate
from app.repositories.base import BaseRepository


class PromptTemplateRepository(BaseRepository[PromptTemplate]):
    """
    Repository operations for managing prompt templates.
    """

    model = PromptTemplate

    async def get_by_name(self, name: str) -> PromptTemplate | None:
        """
        Fetch a template by its unique name.
        """
        stmt = select(self.model).where(self.model.name == name)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def get_by_generation_type(self, gen_type: str) -> PromptTemplate | None:
        """
        Fetch a template by its generation type.
        Prefers custom templates over system defaults.
        """
        stmt = (
            select(self.model)
            .where(self.model.generation_type == gen_type)
            .order_by(self.model.is_system_default.asc())  # False (custom) comes before True (default)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()
