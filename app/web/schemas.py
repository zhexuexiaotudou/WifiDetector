from typing import Literal

from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    status: str
    note: str = Field(default="", max_length=500)


class AllowlistRequest(BaseModel):
    room_id: str
    device_id: str = Field(pattern=r"^dev_[0-9a-f]{16}$")
    label: str
    note: str = Field(default="", max_length=500)


class ReportedDeviceRequest(BaseModel):
    room_id: str
    label: str = Field(min_length=1, max_length=80)
    device_type: Literal["手机", "平板", "个人电脑", "电视", "其他"]
    usage_state: Literal["已连接（使用未知）", "使用中", "待机", "关闭", "离线", "未知"]
    note: str = Field(default="", max_length=500)


class ClearRequest(BaseModel):
    confirmation: str
