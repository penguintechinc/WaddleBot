#!/usr/bin/env python3
import os
import sys
from py4web import action, request, response
import logging

# Add the parent directory to the path to import libs
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config

# Import controllers
import controllers.admin

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info(f"Kong Admin Broker {Config.MODULE_VERSION} starting up")
logger.info(f"Kong Admin URL: {Config.KONG_ADMIN_URL}")

if __name__ == "__main__":
    import py4web
    py4web.main()