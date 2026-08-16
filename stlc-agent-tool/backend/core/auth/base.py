from typing import Protocol, List, Optional
from pydantic import BaseModel

class UserIdentity(BaseModel):
    username: str
    role_name: str
    must_reset_password: bool

class AuthBackend(Protocol):
    """
    Protocol for authentication backends to allow pluggable auth (e.g. Local, SAML, OIDC).
    """
    def authenticate(self, username: str, password: str, ip_address: str) -> Optional[UserIdentity]:
        """
        Authenticates a user and returns their identity, or None if authentication fails.
        """
        ...
        
    def get_user_projects(self, username: str) -> List[str]:
        """
        Returns a list of project names that the user is assigned to.
        """
        ...
