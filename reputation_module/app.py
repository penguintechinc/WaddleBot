"""
Reputation module py4web application
"""

from py4web import action, request, response, HTTP
from py4web.core import Fixture
import os
import logging

from .models import db
from .controllers import reputation_controller
from .services.reputation_service import ReputationService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize reputation service
reputation_service = ReputationService()

# Health check endpoint
@action("health", method=["GET"])
def health():
    """Health check endpoint"""
    try:
        # Test database connection
        db.executesql("SELECT 1")
        return {"status": "healthy", "module": "reputation", "version": "1.0.0"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTP(500, f"Health check failed: {str(e)}")

# Initialize global community on startup
@action("init", method=["POST"])
def initialize():
    """Initialize global community and default reputation scores"""
    try:
        result = reputation_service.initialize_global_community()
        return {"success": True, "message": "Global community initialized", "data": result}
    except Exception as e:
        logger.error(f"Initialization failed: {str(e)}")
        raise HTTP(500, f"Initialization failed: {str(e)}")

if __name__ == "__main__":
    # Auto-initialize on startup
    try:
        reputation_service.initialize_global_community()
        logger.info("Global community initialized on startup")
    except Exception as e:
        logger.error(f"Failed to initialize global community: {str(e)}")