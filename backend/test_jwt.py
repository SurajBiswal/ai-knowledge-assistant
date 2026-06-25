from app.core.security import (
    create_access_token,
    verify_token,
)

token = create_access_token(
    "suraj-user-id"
)

print("Generated Token:")
print(token)

print("\nDecoded User ID:")
print(
    verify_token(token)
)