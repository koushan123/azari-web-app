from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

RoleName = Annotated[str, Field(min_length=1, max_length=50)]


class UserRolesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roles: list[RoleName] = Field(max_length=50)


class UserStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool
