import arq

async def create_pool():
    """Create ARQ Redis pool for job enqueueing"""
    return await arq.create_pool(arq.connections.RedisSettings(host='redis', port=6379))

__all__ = ["create_pool"]
