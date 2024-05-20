
from fastapi import APIRouter, HTTPException
import ormar
import ormar.exceptions
from pydantic import BaseModel

from server.db.models.iam import UserKeyPair
from server.web.api.iam.utils import add_public_key, remove_public_key


api_router = APIRouter()

class UpdateKeyRequest(BaseModel):
    public_key: str

@api_router.post("/ssh_key")
async def gen_key_pair(user_id: str, rbody: UpdateKeyRequest) -> UserKeyPair:
    """Generate a new key pair for a user."""
    try:
        old_key_pair = await UserKeyPair.objects.get(user_id=user_id)
        if old_key_pair:
            await UserKeyPair.objects.delete(user_id=user_id)
            remove_public_key(user_id)
    except ormar.exceptions.NoMatch:
        pass
    finally:
        add_public_key(user_id)
        key = await UserKeyPair.objects.create(
          user_id=user_id,
          public_key=rbody.public_key
        )

    return key

@api_router.get("/ssh_key")
async def get_key_pair(user_id: str) -> UserKeyPair:
    """Get the key pair for a user."""
    try:
      key = await UserKeyPair.objects.get(user_id=user_id)
      return key
    except ormar.exceptions.NoMatch:
        raise HTTPException(status_code=404, detail=f"Key pair for user {user_id} not found")        