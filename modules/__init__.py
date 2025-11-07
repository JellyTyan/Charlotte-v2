import os
import importlib
import logging

logger = logging.getLogger(__name__)

current_dir = os.path.dirname(__file__)
for item in os.listdir(current_dir):
    item_path = os.path.join(current_dir, item)
    if os.path.isdir(item_path) and not item.startswith('__'):
        try:
            importlib.import_module(f'modules.{item}')
            logger.info(f"📦 Module '{item}' loaded successfully")
        except ImportError as e:
            logger.warning(f"⚠️ Failed to load module '{item}': {e}")
