"""Custom SQLAlchemy column types shared by the domain models."""

from typing import Any

from pydantic import BaseModel
from sqlalchemy import JSON
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class PydanticListJSON(TypeDecorator[list[Any]]):
    """JSON column holding a list of pydantic models.

    Models are dumped to plain JSON on write and re-validated back into the
    configured model type on read, so round-tripping through the database
    preserves the attribute access the application code relies on.
    """

    impl = JSON
    cache_ok = True

    def __init__(self, model: type[BaseModel], *args: Any, **kwargs: Any) -> None:
        self.model = model
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:  # noqa: ARG002
        if value is None:
            return None
        return [
            item.model_dump(mode="json") if isinstance(item, BaseModel) else item for item in value
        ]

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:  # noqa: ARG002
        if value is None:
            return None
        return [
            item if isinstance(item, self.model) else self.model.model_validate(item)
            for item in value
        ]
