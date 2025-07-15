"""
Community module py4web application
"""

from py4web import action, request, response, HTTP
import os
import logging
import json

from .models import db
from .services.community_command_service import CommunityCommandService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize community command service
community_service = CommunityCommandService()

# Health check endpoint
@action("health", method=["GET"])
def health():
    """Health check endpoint"""
    try:
        # Test database connection
        db.executesql("SELECT 1")
        return {"status": "healthy", "module": "community", "version": "1.0.0"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTP(500, f"Health check failed: {str(e)}")

# Main community command endpoint
@action("community", method=["POST"])
def handle_community_command():
    """Handle community command requests"""
    try:
        command_data = request.json
        if not command_data:
            raise HTTP(400, "No command data provided")
        
        # Validate required fields
        required_fields = ["user_id", "entity_id", "message_content", "session_id"]
        missing_fields = [field for field in required_fields if field not in command_data]
        if missing_fields:
            raise HTTP(400, f"Missing required fields: {', '.join(missing_fields)}")
        
        # Parse command
        user_id = command_data["user_id"]
        entity_id = command_data["entity_id"]
        message_content = command_data["message_content"]
        session_id = command_data["session_id"]
        execution_id = command_data.get("execution_id", "")
        
        # Process the community command
        result = community_service.process_command(
            user_id=user_id,
            entity_id=entity_id,
            message_content=message_content,
            session_id=session_id,
            execution_id=execution_id
        )
        
        if result["success"]:
            # Return appropriate response type based on result
            if result["response_type"] == "form":
                return {
                    "success": True,
                    "response_action": "form",
                    "session_id": session_id,
                    "execution_id": execution_id,
                    "module_name": "community",
                    "form_title": result["form_title"],
                    "form_description": result["form_description"],
                    "form_fields": result["form_fields"],
                    "form_submit_url": result["form_submit_url"],
                    "form_submit_method": result.get("form_submit_method", "POST"),
                    "form_callback_url": result.get("form_callback_url", "")
                }
            else:
                return {
                    "success": True,
                    "response_action": "chat",
                    "session_id": session_id,
                    "execution_id": execution_id,
                    "module_name": "community",
                    "chat_message": result["message"]
                }
        else:
            return {
                "success": False,
                "response_action": "chat",
                "session_id": session_id,
                "execution_id": execution_id,
                "module_name": "community",
                "chat_message": result["message"],
                "error_message": result.get("error", "")
            }
            
    except Exception as e:
        logger.error(f"Error handling community command: {str(e)}")
        return {
            "success": False,
            "response_action": "chat",
            "session_id": command_data.get("session_id", ""),
            "execution_id": command_data.get("execution_id", ""),
            "module_name": "community",
            "chat_message": "An error occurred while processing your command.",
            "error_message": str(e)
        }

# Form submission endpoint
@action("community/form", method=["POST"])
def handle_form_submission():
    """Handle form submissions from community commands"""
    try:
        form_data = request.json
        if not form_data:
            raise HTTP(400, "No form data provided")
        
        # Process form submission
        result = community_service.process_form_submission(form_data)
        
        if result["success"]:
            return {
                "success": True,
                "response_action": "chat",
                "module_name": "community",
                "chat_message": result["message"]
            }
        else:
            return {
                "success": False,
                "response_action": "chat",
                "module_name": "community",
                "chat_message": result["message"],
                "error_message": result.get("error", "")
            }
            
    except Exception as e:
        logger.error(f"Error handling form submission: {str(e)}")
        return {
            "success": False,
            "response_action": "chat",
            "module_name": "community",
            "chat_message": "An error occurred while processing your form submission.",
            "error_message": str(e)
        }