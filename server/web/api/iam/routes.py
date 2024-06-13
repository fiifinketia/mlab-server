
from fastapi import APIRouter, HTTPException, Request
import ormar
import ormar.exceptions
from pydantic import BaseModel

from server.db.models.iam import UserKeyPair
from server.services.git.main import GitService
from server.web.api.iam.utils import add_public_key, remove_public_key


api_router = APIRouter()

class UpdateKeyRequest(BaseModel):
    public_key: str

@api_router.post("/ssh_key", tags=["iam"])
async def gen_key_pair(req: Request, rbody: UpdateKeyRequest) -> UserKeyPair:
    """Generate a new key pair for a user."""
    user_id = req.state.user_id
    git = GitService()
    # try:
    #     old_key_pair = await UserKeyPair.objects.get(user_id=user_id)
    #     if old_key_pair:
    #         await UserKeyPair.objects.delete(user_id=user_id)
    #         git.delete_ssh_key(key_id=old_key_pair.public_key, username=user_id)
    # except ormar.exceptions.NoMatch:
    #     pass
    # finally:
    #     git.add_ssh_key(key=rbody.public_key, username=user_id, title="mlab")
    #     key = await UserKeyPair.objects.create(
    #       user_id=user_id,
    #       public_key=rbody.public_key
    #     )
    git.add_ssh_key(key=rbody.public_key, username=user_id, title="mlab")
    key = await UserKeyPair.objects.create(
        user_id=user_id,
        public_key=rbody.public_key
    )
    return key

@api_router.get("/ssh_key", tags=["iam"])
async def get_key_pair(req: Request) -> UserKeyPair:
    """Get the key pair for a user."""
    user_id = req.state.user_id
    try:
      key = await UserKeyPair.objects.get(user_id=user_id)
      return key
    except ormar.exceptions.NoMatch:
        raise HTTPException(status_code=404, detail=f"Key pair for user {user_id} not found")
