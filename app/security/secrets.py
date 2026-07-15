from __future__ import annotations

import getpass
import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RouterCredentials:
    username: str
    password: str


def load_credentials(interactive: bool = False) -> RouterCredentials | None:
    username = os.getenv("H10E31_USERNAME")
    password = os.getenv("H10E31_PASSWORD")
    if username and password:
        return RouterCredentials(username, password)
    if not interactive:
        return None
    entered_user = input("网关用户名（不会保存）: ").strip()
    entered_password = getpass.getpass("网关密码（不会保存）: ")
    return (
        RouterCredentials(entered_user, entered_password)
        if entered_user and entered_password
        else None
    )
