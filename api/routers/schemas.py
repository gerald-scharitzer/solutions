from pydantic import BaseModel

class AuthorizationResponse(BaseModel):
    state: str
    code: str

class GithubUser(BaseModel):
    login: str
    name: str
    company: str = None
    location: str = None
    email: str = None
    avatar_url: str

class GoogleUser(BaseModel):
    login: str
    name: str
    company: str = None
    location: str = None
    email: str
    picture: str

class User(BaseModel):
    login: str
    name: str
    company: str = None
    location: str = None
    email: str
    picture: str = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class Url(BaseModel):
    url: str
