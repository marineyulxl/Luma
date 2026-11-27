"""所有者初始化的输入校验。"""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, SecretStr, field_validator


def validate_new_password(password: SecretStr) -> SecretStr:
    value = password.get_secret_value()
    if not value.strip():
        raise ValueError("密码不能全部为空白字符")
    if len(value) < 15 and not (
        any(char.isalpha() for char in value) and any(char.isdigit() for char in value)
    ):
        raise ValueError("8–14 位密码需要同时包含字母和数字，15 位以上允许任意组合")
    return password


NewPassword = Annotated[
    SecretStr, Field(min_length=8, max_length=128), AfterValidator(validate_new_password)
]


class OwnerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    username: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    password: NewPassword

    @field_validator("username", "display_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("名称不能为空或包含控制字符")
        return value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if any(char.isspace() for char in value):
            raise ValueError("登录账号不能包含空白字符")
        return value
