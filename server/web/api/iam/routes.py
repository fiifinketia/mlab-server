
from fastapi import APIRouter, HTTPException

from server.db.models.iam import UserKeyPair
from server.web.api.iam.utils import generate_key_pair, remove_key_pair


api_router = APIRouter()

@api_router.post("/ssh_key")
async def gen_key_pair(user_id: str) -> dict[str, bytes]:
    """Generate a new key pair for a user."""
    old_key_pair = UserKeyPair.objects.get(user_id=user_id)
    if old_key_pair:
        await UserKeyPair.objects.delete(user_id=user_id)
        remove_key_pair(user_id)
    new_key_pair = generate_key_pair(user_id)
    await UserKeyPair.objects.create(
      user_id=user_id,
      public_key=new_key_pair[0]
    )

    key_pair = {
      "public_key": new_key_pair[0],
      "private_key": new_key_pair[1]
    }

    return key_pair

@api_router.get("/ssh_key")
async def get_key_pair(user_id: str) -> dict[str, bytes|str]:
    """Get the key pair for a user."""
    key_pair = await UserKeyPair.objects.get(user_id=user_id)
    if key_pair:
        return {
          "public_key": key_pair.public_key,
          "private_key": "*********************************"
        }
    else:
        raise HTTPException(status_code=404, detail=f"Key pair for user {user_id} not found")