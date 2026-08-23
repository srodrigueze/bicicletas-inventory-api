from sqlmodel import Field, SQLModel


class Client(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    full_name: str = Field(max_length=100)
    document: str = Field(max_length=14, unique=True, index=True)
    phone: str = Field(max_length=15)
