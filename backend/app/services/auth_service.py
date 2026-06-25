from app.repositories.user_repository import UserRepository
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)

class AuthService:

    def __init__(
        self,
        user_repository: UserRepository,
    ):
        self.user_repository = user_repository

    def register_user(
        self,
        name: str,
        email: str,
        password: str,
    ):
        
        existing_user = (
            self.user_repository.get_by_email(
                email
            )
        ) 
        if existing_user:
            raise ValueError(
                "Email already registered"
            )
        
        password_hash = hash_password(password)

        user = self.user_repository.create(
            name=name,
            email=email,
            password_hash=password_hash,
        )
        
        return user
    

    def authenticate_user(
        self,
        email: str,
        password: str,
    ):
        user = self.user_repository.get_by_email(
            email
        )
        if not user:
            raise ValueError(
                "Invalid email or password"
            ) 
        
        if not verify_password(
            password,
            user.password_hash,
        ):
            raise ValueError(
                "Invalid email or password"
            )   
        token = create_access_token(
            str(user.id)
        )

        return token