"""Shared Pydantic base classes."""

from pydantic import BaseModel, ConfigDict


class OutMixin(BaseModel):
    """Response schema base — allows building straight from ORM objects."""

    model_config = ConfigDict(from_attributes=True)
