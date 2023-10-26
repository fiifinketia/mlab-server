from databases import Database

from server.settings import settings

database = Database(str(settings.db_url))
