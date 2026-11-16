from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class RegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length="100")
    email: EmailStr = Field(default="dukybiz@gmail.com")
    password: str = Field(min_length=8, max_length=120)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value:str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def password_needs_letter_and_number(cls, value:str) -> str:
        if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("password must contain at least one letter and one number")
        return value

class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field()
    password: str = Field()