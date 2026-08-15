from pydantic import BaseModel, ConfigDict, Field


class UserRead(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str = Field(..., max_length=50)
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
