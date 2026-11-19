from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """Data a visitor sends to create an account."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=100, examples=["Ada Obi"])
    email: EmailStr = Field(examples=["ada@example.com"])
    password: str = Field(min_length=8, max_length=128, examples=["secret123"])

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def password_needs_letter_and_number(cls, value: str) -> str:
        if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("Password must contain at least one letter and one number")
        return value


class LoginRequest(BaseModel):
    """Data a user sends to log in."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr = Field(examples=["ada@example.com"])
    password: str = Field(min_length=1, examples=["secret123"])

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class TokenResponse(BaseModel):
    """What the API returns after a successful login."""

    access_token: str = Field(examples=["eyJhbGciOiJIUzI1NiIs..."])
    token_type: str = Field(default="bearer", examples=["bearer"])