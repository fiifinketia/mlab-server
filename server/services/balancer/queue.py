"""
This module implements a queue manager for handling tasks.
"""
from typing import Any
from redis.asyncio import ConnectionPool, Redis

from server.settings import settings


class QueueManager:
    """
    Class to manage queue of requests
    """
    def __init__(self) -> None:
        """
        Initialize the QueueManager class.

        This method creates a connection pool to a Redis server using the provided
        Redis URL from the settings.

        Parameters:
        None

        Returns:
        None
        """
        self.redis_pool: Any = ConnectionPool.from_url(
            str(settings.redis_url),
        )

    async def add(self, queue_name: str, task: Any) -> None:
        """
        Add a task to a specified queue in Redis.

        This method connects to the Redis server using the existing connection pool,
        and then uses the 'rpush' command to add the task to the end of the specified queue.
        After adding the task, the connection to the Redis server is closed.

        Parameters:
        queue_name (str): The name of the queue to add the task to.
        task (Any): The task to be added to the queue.

        Returns:
        None
        """
        redis = Redis(connection_pool=self.redis_pool)
        await redis.rpush(queue_name, task)
        await redis.close()

    async def list(self, queue_name: str) -> Any:
        """
        List all tasks in a specified queue.

        This method connects to the Redis server using the existing connection pool,
        retrieves all tasks from the specified queue using the 'lrange' command,
        and returns the tasks as a list.

        Parameters:
        queue_name (str): The name of the queue from which to retrieve tasks.

        Returns:
        Any: A list of tasks in the specified queue.

        Note:
        The connection to the Redis server is automatically closed after retrieving the tasks.
        """
        redis = Redis(connection_pool=self.redis_pool)
        tasks = await redis.lrange(queue_name, 0, -1)
        await redis.close()
        return tasks

    async def remove(self, queue_name: str, task: Any) -> None:
        """
        Remove a task from a specified queue by its index.

        This method connects to the Redis server using the existing connection pool,
        and then uses the 'lrem' command to remove the first occurrence of the specified task
        from the specified queue. After removing the task, the connection to the Redis server is closed.

        Parameters:
        queue_name (str): The name of the queue from which to remove the task.
        task (Any): The task to be removed from the queue.

        Returns:
        None

        Note:
        This method only removes the first occurrence of the specified task.
        If the task appears multiple times in the queue, only the first occurrence will be removed.
        """
        redis = Redis(connection_pool=self.redis_pool)
        await redis.lrem(queue_name, 1, task)
        await redis.close()
