from pydantic import BaseModel, ConfigDict, Field


class ClientData(BaseModel):
    full_name: str = Field(..., max_length=100)
    document: str = Field(..., min_length=6, max_length=14)
    phone: str = Field(..., max_length=15)


class ClientRead(BaseModel):
    id: int
    full_name: str
    document: str
    phone: str

    model_config = ConfigDict(from_attributes=True)
