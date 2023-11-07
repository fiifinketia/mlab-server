""""""
from server.db.models.ml_models import Model


async def get_all() -> list[Model]:
    """Get all models."""
    # Fetch all models from database
    models = await Model.objects.all()
    # Return models
    return models
