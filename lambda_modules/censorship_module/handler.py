"""
WaddleBot Censorship Module - AWS Lambda Function
Handles profanity filtering and content moderation for all chat messages
"""

import json
import re
import logging
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
import boto3
from boto3.dynamodb.conditions import Key

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# DynamoDB client for storing community-specific word lists
dynamodb = boto3.resource('dynamodb')

# Default banned words and phrases (common profanity and slurs)
# Note: Using leetspeak variations and common substitutions
DEFAULT_BANNED_WORDS = {
    # Profanity (with common variations)
    'f*ck', 'f**k', 'fck', 'fuk', 'phuck', 'f u c k', 'f.u.c.k',
    'sh*t', 'sh1t', 'sh!t', 's h i t', 's.h.i.t',
    'b*tch', 'b1tch', 'b!tch', 'biatch', 'beyotch',
    'a**', 'a$$', '@ss', 'a s s',
    'd*mn', 'dayum', 'd a m n',
    'h*ll', 'h3ll', 'h e l l',
    'p*ss', 'p!ss', 'p1ss',
    'c*nt', 'kunt',
    'd*ck', 'd1ck', 'd!ck', 'dik',
    'p*ssy', 'pu$$y', 'puss1',
    'c*ck', 'c0ck', 'cawk',
    'wh*re', 'wh0re', 'h0e', 'h03',
    
    # Slurs and hate speech (zero tolerance)
    'n*gger', 'n*gga', 'n1gg', 'nigg@',
    'f*ggot', 'f*g', 'fgt', 'f@g',
    'r*tard', 'ret@rd', 'r3tard',
    'tr*nny', 'tr@nny',
    'k*ke', 'kik3',
    'sp*c', 'sp1c',
    'ch*nk', 'ch1nk',
    'g*ok', 'g00k',
    'w*tback', 'wetb@ck',
    
    # Sexual content
    'porn', 'p0rn', 'pr0n',
    'sex', 's3x', 'secks',
    'nude', 'nud3', 'n00d',
    'penis', 'pen1s', 'p3nis',
    'vagina', 'vag1na', 'v@gina',
    'boob', 'b00b', 'bewb',
    'tit', 't1t', 'titt',
    
    # Drug references
    'cocaine', 'coke', 'c0ke',
    'heroin', 'her0in', 'h3roin',
    'meth', 'm3th', 'crystal',
    'weed', 'w33d', '420',
    'drug', 'dr*g', 'drugz',
    
    # Violence and threats
    'kill', 'k!ll', 'k1ll',
    'murder', 'murd3r',
    'rape', 'r@pe', 'r8pe',
    'suicide', 'suicid3', 'kys',
    'die', 'd!e', 'dy3',
}

# Common substitution patterns
SUBSTITUTION_PATTERNS = {
    '@': 'a',
    '0': 'o',
    '1': 'i',
    '3': 'e',
    '4': 'a',
    '5': 's',
    '7': 't',
    '8': 'b',
    '!': 'i',
    '$': 's',
    '+': 't',
    '*': '',
}

class CensorshipFilter:
    """Main censorship filter class"""
    
    def __init__(self):
        self.word_table = None
        self.community_table = None
        try:
            self.word_table = dynamodb.Table('waddlebot_censored_words')
            self.community_table = dynamodb.Table('waddlebot_community_settings')
        except Exception as e:
            logger.warning(f"DynamoDB tables not available: {e}")
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for better matching"""
        # Convert to lowercase
        text = text.lower()
        
        # Replace common substitutions
        for char, replacement in SUBSTITUTION_PATTERNS.items():
            text = text.replace(char, replacement)
        
        # Remove extra spaces and special characters
        text = re.sub(r'[^a-z0-9\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def get_community_words(self, community_id: str) -> Tuple[Set[str], Set[str]]:
        """Get community-specific banned and allowed words"""
        banned = set()
        allowed = set()
        
        if not self.word_table:
            return banned, allowed
        
        try:
            # Get community-specific words
            response = self.word_table.query(
                KeyConditionExpression=Key('community_id').eq(community_id)
            )
            
            for item in response.get('Items', []):
                word = item.get('word', '').lower()
                if item.get('action') == 'ban':
                    banned.add(word)
                elif item.get('action') == 'allow':
                    allowed.add(word)
            
            # Check if community uses default list
            if self.community_table:
                settings = self.community_table.get_item(
                    Key={'community_id': community_id}
                ).get('Item', {})
                
                if settings.get('use_default_filter', True):
                    banned.update(DEFAULT_BANNED_WORDS)
        
        except Exception as e:
            logger.error(f"Error fetching community words: {e}")
            # Fall back to defaults
            banned.update(DEFAULT_BANNED_WORDS)
        
        return banned, allowed
    
    def check_message(self, message: str, community_id: str) -> Dict:
        """Check message for censored content"""
        original_message = message
        normalized_message = self.normalize_text(message)
        
        # Get community-specific words
        banned_words, allowed_words = self.get_community_words(community_id)
        
        # Check for violations
        found_violations = []
        severity = 'clean'
        action = 'pass'
        
        # Check each word and phrase
        words_to_check = set()
        
        # Add individual words
        words_to_check.update(normalized_message.split())
        
        # Add bigrams (two-word phrases)
        words = normalized_message.split()
        for i in range(len(words) - 1):
            words_to_check.add(f"{words[i]} {words[i+1]}")
        
        # Check against banned words
        for word in words_to_check:
            if word in allowed_words:
                continue  # Skip if explicitly allowed
            
            for banned in banned_words:
                normalized_banned = self.normalize_text(banned)
                if normalized_banned in word or word in normalized_banned:
                    found_violations.append(banned)
                    
                    # Determine severity
                    if any(slur in banned.lower() for slur in ['n*gg', 'f*g', 'r*tard', 'tr*nny']):
                        severity = 'severe'
                        action = 'block'
                    elif severity != 'severe':
                        severity = 'moderate'
                        if action != 'block':
                            action = 'warn'
        
        # Generate censored version
        censored_message = self.censor_message(original_message, found_violations)
        
        return {
            'original': original_message,
            'censored': censored_message,
            'violations': found_violations,
            'severity': severity,
            'action': action,
            'clean': len(found_violations) == 0
        }
    
    def censor_message(self, message: str, violations: List[str]) -> str:
        """Replace violations with asterisks"""
        censored = message
        
        for violation in violations:
            # Create pattern for case-insensitive replacement
            pattern = re.compile(re.escape(violation), re.IGNORECASE)
            replacement = violation[0] + '*' * (len(violation) - 2) + violation[-1] if len(violation) > 2 else '*' * len(violation)
            censored = pattern.sub(replacement, censored)
        
        return censored

def lambda_handler(event, context):
    """
    Lambda handler for censorship module
    Expected event format:
    {
        "session_id": "uuid",
        "community_id": "community_identifier",
        "entity_id": "platform:server:channel",
        "user_id": "user_identifier",
        "user_name": "username",
        "message": "message content",
        "platform": "discord/twitch/slack",
        "action": "check/add_word/remove_word/get_settings"
    }
    """
    
    try:
        # Parse the event
        if isinstance(event, str):
            event = json.loads(event)
        
        action = event.get('action', 'check')
        filter = CensorshipFilter()
        
        if action == 'check':
            # Check message for profanity
            message = event.get('message', '')
            community_id = event.get('community_id', 'default')
            
            if not message:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'No message provided'})
                }
            
            result = filter.check_message(message, community_id)
            
            # Log if violations found
            if not result['clean']:
                logger.info(f"Violations found in community {community_id}: {result['violations']}")
            
            # Prepare response for router
            response = {
                'session_id': event.get('session_id'),
                'success': True,
                'response_action': 'moderation',
                'response_data': {
                    'original_message': result['original'],
                    'censored_message': result['censored'],
                    'clean': result['clean'],
                    'violations': result['violations'],
                    'severity': result['severity'],
                    'suggested_action': result['action']
                },
                'module_name': 'censorship_module',
                'processing_time_ms': 10
            }
            
            # If message should be blocked, add chat response
            if result['action'] == 'block':
                response['chat_message'] = f"⚠️ Message blocked due to inappropriate content."
            elif result['action'] == 'warn':
                response['chat_message'] = f"⚠️ Warning: Please watch your language."
            
            return {
                'statusCode': 200,
                'body': json.dumps(response)
            }
        
        elif action == 'add_word':
            # Add word to community's list (admin only)
            community_id = event.get('community_id')
            word = event.get('word', '').lower()
            word_action = event.get('word_action', 'ban')  # ban or allow
            added_by = event.get('user_name', 'admin')
            
            if not community_id or not word:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Missing community_id or word'})
                }
            
            # Add to DynamoDB
            if filter.word_table:
                filter.word_table.put_item(Item={
                    'community_id': community_id,
                    'word': word,
                    'action': word_action,
                    'added_by': added_by,
                    'added_at': datetime.utcnow().isoformat()
                })
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'message': f"Word '{word}' added to {word_action} list"
                })
            }
        
        elif action == 'remove_word':
            # Remove word from community's list (admin only)
            community_id = event.get('community_id')
            word = event.get('word', '').lower()
            
            if not community_id or not word:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Missing community_id or word'})
                }
            
            # Remove from DynamoDB
            if filter.word_table:
                filter.word_table.delete_item(
                    Key={
                        'community_id': community_id,
                        'word': word
                    }
                )
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'message': f"Word '{word}' removed"
                })
            }
        
        elif action == 'get_settings':
            # Get community settings
            community_id = event.get('community_id')
            
            if not community_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Missing community_id'})
                }
            
            banned_words, allowed_words = filter.get_community_words(community_id)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'banned_words': list(banned_words),
                    'allowed_words': list(allowed_words),
                    'uses_default': True  # TODO: Get from community settings
                })
            }
        
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Unknown action: {action}'})
            }
    
    except Exception as e:
        logger.error(f"Error in censorship module: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'session_id': event.get('session_id')
            })
        }