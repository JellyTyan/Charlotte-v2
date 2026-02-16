"""ARQ worker pool management"""
import arq
from arq.connections import RedisSettings

# Global pool instances per queue
_pools = {}


async def get_arq_pool(queue_name: str = 'light'):
    """Get or create ARQ Redis pool for job enqueueing"""
    global _pools
    if queue_name not in _pools:
        _pools[queue_name] = await arq.create_pool(
            RedisSettings(host='redis', port=6379),
            default_queue_name=queue_name
        )
    return _pools[queue_name]


async def close_arq_pool():
    """Close all ARQ pools"""
    global _pools
    for pool in _pools.values():
        await pool.close()
    _pools.clear()
