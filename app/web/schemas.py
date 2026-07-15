from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    status: str
    note: str = Field(default="", max_length=500)


class AllowlistRequest(BaseModel):
    room_id: str
    device_id: str = Field(pattern=r"^dev_[0-9a-f]{16}$")
    label: str
    note: str = Field(default="", max_length=500)


class ClearRequest(BaseModel):
    confirmation: str
