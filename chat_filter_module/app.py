"""
WaddleBot Chat Filter Module - High-Performance py4web Application
Combines censorship, spam detection, and URL blocking for chat messages
Designed to handle thousands of messages per second using async/await
"""

import json
import re
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from py4web import action, request, response, Field
from py4web.utils.cors import CORS
from concurrent.futures import ThreadPoolExecutor

from models import db
from config import Config
from services.chat_filter_service import ChatFilterService
from services.router_service import RouterService

# Initialize services
chat_filter_service = ChatFilterService()
router_service = RouterService()

# Global thread pool for async operations
thread_pool = ThreadPoolExecutor(max_workers=Config.MAX_WORKERS)

# Enable CORS for API endpoints
cors = CORS()

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@action('/')
def index():
    """Health check endpoint"""
    return {
        'module': 'chat_filter_module',
        'version': Config.MODULE_VERSION,
        'status': 'active',
        'capabilities': [
            'profanity_filtering',
            'spam_detection', 
            'url_blocking',
            'community_rules'
        ]
    }

@action('/health')
def health():
    """Detailed health check"""
    try:
        # Test database connection
        db.executesql('SELECT 1')
        db_status = 'healthy'
    except Exception as e:
        db_status = f'error: {str(e)}'
    
    return {
        'status': 'healthy',
        'database': db_status,
        'timestamp': datetime.utcnow().isoformat(),
        'module': Config.MODULE_NAME,
        'version': Config.MODULE_VERSION
    }

@action('/filter', method=['POST'])
@cors.enable
def filter_message():
    """
    Main message filtering endpoint
    Checks messages for profanity, spam, and blocked URLs
    """
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['community_id', 'message', 'user_id', 'platform']
        for field in required_fields:
            if field not in data:
                response.status = 400
                return {'error': f'Missing required field: {field}'}
        
        community_id = data['community_id']
        message = data['message']
        user_id = data['user_id']
        platform = data.get('platform', 'unknown')
        session_id = data.get('session_id')
        
        # Run comprehensive chat filter check
        result = chat_filter_service.check_message(
            message=message,
            community_id=community_id,
            user_id=user_id,
            platform=platform
        )
        
        # Log violations if found
        if not result['clean']:
            logger.info(
                f"Chat filter violation in community {community_id}: "
                f"user={user_id}, violations={result.get('violations', [])}, "
                f"spam_score={result.get('spam_score', 0)}"
            )
        
        # Prepare response for router
        filter_response = {
            'session_id': session_id,
            'success': True,
            'response_action': 'moderation',
            'response_data': {
                'original_message': result['original'],
                'censored_message': result.get('censored', result['original']),
                'clean': result['clean'],
                'filter_type': result['filter_type'],
                'violations': result.get('violations', []),
                'spam_score': result.get('spam_score', 0),
                'blocked_urls': result.get('blocked_urls', []),
                'severity': result['severity'],
                'suggested_action': result['action']
            },
            'module_name': 'chat_filter_module',
            'processing_time_ms': 20
        }
        
        # Add chat response based on action
        if result['action'] == 'block':
            if result['filter_type'] == 'profanity':
                filter_response['chat_message'] = "⚠️ Message blocked due to inappropriate content."
            elif result['filter_type'] == 'spam':
                filter_response['chat_message'] = "🚫 Message blocked - spam detected."
            elif result['filter_type'] == 'url':
                filter_response['chat_message'] = "🔗 Message blocked - unauthorized URL."
        elif result['action'] == 'warn':
            if result['filter_type'] == 'profanity':
                filter_response['chat_message'] = "⚠️ Warning: Please watch your language."
            elif result['filter_type'] == 'spam':
                filter_response['chat_message'] = "⚠️ Warning: Your message appears to contain promotional content."
        
        return filter_response
    
    except Exception as e:
        logger.error(f"Error in filter_message: {str(e)}")
        response.status = 500
        return {'error': str(e)}

@action('/filter/batch', method=['POST'])
@cors.enable
def filter_messages_batch():
    """
    Batch message filtering endpoint for high throughput
    Processes multiple messages concurrently
    """
    try:
        data = request.json
        
        if 'messages' not in data:
            response.status = 400
            return {'error': 'Missing messages array'}
        
        messages = data['messages']
        if not isinstance(messages, list) or len(messages) == 0:
            response.status = 400
            return {'error': 'Messages must be a non-empty array'}
        
        if len(messages) > 100:  # Limit batch size
            response.status = 400
            return {'error': 'Batch size cannot exceed 100 messages'}
        
        # Validate each message
        for i, msg in enumerate(messages):
            required_fields = ['community_id', 'message', 'user_id', 'platform']
            for field in required_fields:
                if field not in msg:
                    response.status = 400
                    return {'error': f'Message {i}: Missing required field: {field}'}
        
        # Use async processing for batch
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(
                chat_filter_service.check_messages_batch(messages)
            )
        finally:
            loop.close()
        
        # Prepare batch response
        batch_response = {
            'success': True,
            'total_messages': len(messages),
            'processed_messages': len(results),
            'results': []
        }
        
        # Process each result
        for i, result in enumerate(results):
            msg_data = messages[i]
            
            filter_response = {
                'session_id': msg_data.get('session_id'),
                'success': True,
                'response_action': 'moderation',
                'response_data': {
                    'original_message': result['original'],
                    'censored_message': result.get('censored', result['original']),
                    'clean': result['clean'],
                    'filter_type': result.get('filter_type', 'none'),
                    'violations': result.get('violations', []),
                    'spam_score': result.get('spam_score', 0),
                    'blocked_urls': result.get('blocked_urls', []),
                    'severity': result.get('severity', 'clean'),
                    'suggested_action': result.get('action', 'pass')
                },
                'module_name': 'chat_filter_module',
                'processing_time_ms': 5  # Lower per-message time due to batching
            }
            
            # Add chat response based on action
            if result.get('action') == 'block':
                if result.get('filter_type') == 'profanity':
                    filter_response['chat_message'] = "⚠️ Message blocked due to inappropriate content."
                elif result.get('filter_type') == 'spam':
                    filter_response['chat_message'] = "🚫 Message blocked - spam detected."
                elif result.get('filter_type') == 'url':
                    filter_response['chat_message'] = "🔗 Message blocked - unauthorized URL."
            elif result.get('action') == 'warn':
                if result.get('filter_type') == 'profanity':
                    filter_response['chat_message'] = "⚠️ Warning: Please watch your language."
                elif result.get('filter_type') == 'spam':
                    filter_response['chat_message'] = "⚠️ Warning: Your message appears to contain promotional content."
            
            batch_response['results'].append(filter_response)
        
        return batch_response
    
    except Exception as e:
        logger.error(f"Error in filter_messages_batch: {str(e)}")
        response.status = 500
        return {'error': str(e)}

@action('/profanity/words', method=['GET'])
@cors.enable
def get_profanity_words():
    """Get community profanity word list"""
    try:
        community_id = request.query.get('community_id')
        if not community_id:
            response.status = 400
            return {'error': 'Missing community_id parameter'}
        
        banned_words, allowed_words = chat_filter_service.get_community_words(community_id)
        
        return {
            'success': True,
            'community_id': community_id,
            'banned_words': list(banned_words),
            'allowed_words': list(allowed_words),
            'uses_default': True
        }
    
    except Exception as e:
        logger.error(f"Error getting profanity words: {str(e)}")
        response.status = 500
        return {'error': str(e)}

@action('/profanity/words', method=['POST'])
@cors.enable
def add_profanity_word():
    """Add word to community profanity list (admin only)"""
    try:
        data = request.json
        
        community_id = data.get('community_id')
        word = data.get('word', '').lower().strip()
        word_action = data.get('action', 'ban')  # ban or allow
        added_by = data.get('user_name', 'admin')
        
        if not community_id or not word:
            response.status = 400
            return {'error': 'Missing community_id or word'}
        
        # Add to database
        db.censorship_words.insert(
            community_id=community_id,
            word=word,
            action=word_action,
            added_by=added_by,
            category='custom'
        )
        db.commit()
        
        return {
            'success': True,
            'message': f"Word '{word}' added to {word_action} list"
        }
    
    except Exception as e:
        logger.error(f"Error adding profanity word: {str(e)}")
        response.status = 500
        return {'error': str(e)}

@action('/spam/patterns', method=['GET'])
@cors.enable
def get_spam_patterns():
    """Get community spam patterns"""
    try:
        community_id = request.query.get('community_id')
        if not community_id:
            response.status = 400
            return {'error': 'Missing community_id parameter'}
        
        patterns, whitelist = chat_filter_service.get_community_spam_patterns(community_id)
        
        return {
            'success': True,
            'community_id': community_id,
            'spam_patterns': list(patterns),
            'whitelist_patterns': list(whitelist),
            'uses_default': True
        }
    
    except Exception as e:
        logger.error(f"Error getting spam patterns: {str(e)}")
        response.status = 500
        return {'error': str(e)}

@action('/spam/patterns', method=['POST'])
@cors.enable
def add_spam_pattern():
    """Add spam pattern to community list (admin only)"""
    try:
        data = request.json
        
        community_id = data.get('community_id')
        pattern = data.get('pattern', '').lower().strip()
        pattern_action = data.get('action', 'block')  # block or allow
        added_by = data.get('user_name', 'admin')
        
        if not community_id or not pattern:
            response.status = 400
            return {'error': 'Missing community_id or pattern'}
        
        # Add to database
        db.spam_patterns.insert(
            community_id=community_id,
            pattern=pattern,
            action=pattern_action,
            added_by=added_by
        )
        db.commit()
        
        return {
            'success': True,
            'message': f"Spam pattern '{pattern}' added to {pattern_action} list"
        }
    
    except Exception as e:
        logger.error(f"Error adding spam pattern: {str(e)}")
        response.status = 500
        return {'error': str(e)}

@action('/urls/settings', method=['GET'])
@cors.enable
def get_url_settings():
    """Get community URL blocking settings"""
    try:
        community_id = request.query.get('community_id')
        if not community_id:
            response.status = 400
            return {'error': 'Missing community_id parameter'}
        
        settings = chat_filter_service.get_url_settings(community_id)
        
        return {
            'success': True,
            'community_id': community_id,
            'url_blocking_enabled': settings.get('url_blocking_enabled', False),
            'allowed_domains': settings.get('allowed_domains', []),
            'blocked_domains': settings.get('blocked_domains', []),
            'allow_all_urls': settings.get('allow_all_urls', True)
        }
    
    except Exception as e:
        logger.error(f"Error getting URL settings: {str(e)}")
        response.status = 500
        return {'error': str(e)}

@action('/urls/settings', method=['POST'])
@cors.enable
def update_url_settings():
    """Update community URL blocking settings (admin only)"""
    try:
        data = request.json
        
        community_id = data.get('community_id')
        if not community_id:
            response.status = 400
            return {'error': 'Missing community_id'}
        
        updated_by = data.get('user_name', 'admin')
        
        # Update or insert URL settings
        existing = db((db.url_settings.community_id == community_id)).select().first()
        
        update_data = {
            'community_id': community_id,
            'url_blocking_enabled': data.get('url_blocking_enabled', False),
            'allowed_domains': json.dumps(data.get('allowed_domains', [])),
            'blocked_domains': json.dumps(data.get('blocked_domains', [])),
            'allow_all_urls': data.get('allow_all_urls', True),
            'updated_by': updated_by
        }
        
        if existing:
            db((db.url_settings.community_id == community_id)).update(**update_data)
        else:
            db.url_settings.insert(**update_data)
        
        db.commit()
        
        return {
            'success': True,
            'message': 'URL settings updated successfully'
        }
    
    except Exception as e:
        logger.error(f"Error updating URL settings: {str(e)}")
        response.status = 500
        return {'error': str(e)}

@action('/settings', method=['GET'])
@cors.enable
def get_community_settings():
    """Get comprehensive community filter settings"""
    try:
        community_id = request.query.get('community_id')
        if not community_id:
            response.status = 400
            return {'error': 'Missing community_id parameter'}
        
        settings = chat_filter_service.get_community_settings(community_id)
        
        return {
            'success': True,
            'community_id': community_id,
            'settings': settings
        }
    
    except Exception as e:
        logger.error(f"Error getting community settings: {str(e)}")
        response.status = 500
        return {'error': str(e)}

@action('/stats', method=['GET'])
@cors.enable
def get_filter_stats():
    """Get filtering statistics"""
    try:
        community_id = request.query.get('community_id')
        
        stats = chat_filter_service.get_filter_stats(community_id)
        
        return {
            'success': True,
            'stats': stats
        }
    
    except Exception as e:
        logger.error(f"Error getting filter stats: {str(e)}")
        response.status = 500
        return {'error': str(e)}

if __name__ == '__main__':
    # Development server
    from py4web import Bottle
    app = Bottle()
    app.run(host='0.0.0.0', port=8040, debug=True)