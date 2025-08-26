"""
WaddleBot Spam Detection Module - AWS Lambda Function
Detects spam messages and promotional content in chat messages
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

# DynamoDB client for storing community-specific spam rules
dynamodb = boto3.resource('dynamodb')

# Default spam patterns and phrases
DEFAULT_SPAM_PATTERNS = {
    # Viewer/follower purchasing
    'buy viewers', 'buy followers', 'get viewers', 'get followers',
    'increase viewers', 'increase followers', 'boost viewers', 'boost followers',
    'real viewers', 'real followers', 'instant viewers', 'instant followers',
    'cheap viewers', 'cheap followers', 'fast viewers', 'fast followers',
    'viewer bot', 'follower bot', 'view bot', 'follow bot',
    
    # Fame/popularity services
    'become famous', 'get famous', 'make you famous', 'famous streamer',
    'go viral', 'viral content', 'trending now', 'popular streamer',
    'instant fame', 'overnight success', 'famous overnight',
    
    # Social media growth
    'grow your channel', 'channel growth', 'stream growth', 'audience growth',
    'subscriber growth', 'follower growth', 'organic growth', 'real growth',
    'engagement boost', 'boost engagement', 'increase engagement',
    'social media marketing', 'smm panel', 'smm service',
    
    # Promotional links and services
    'check my bio', 'link in bio', 'click my profile', 'visit my page',
    'dm for details', 'dm me for', 'message me for', 'contact me for',
    'promo code', 'discount code', 'use code', 'coupon code',
    'limited time', 'act now', 'hurry up', 'dont miss',
    'special offer', 'exclusive offer', 'amazing deal', 'best price',
    
    # Crypto/investment spam
    'easy money', 'quick money', 'fast cash', 'make money fast',
    'work from home', 'online income', 'passive income', 'side hustle',
    'crypto trading', 'forex trading', 'investment opportunity',
    'double your money', 'guaranteed profit', 'risk free',
    
    # Discord/social invites
    'join my discord', 'discord server', 'join my server', 'invite link',
    'free nitro', 'nitro giveaway', 'gift card', 'steam key',
    'check this out', 'you should see', 'amazing content',
    
    # Generic spam indicators
    'www.', 'http://', 'https://', '.com', '.net', '.org',
    'subscribe to', 'follow me on', 'add me on', 'friend me',
    'like and subscribe', 'smash that like', 'hit the bell',
    '100% real', '100% legit', 'no scam', 'trusted service',
    
    # Repetitive/caps patterns (handled separately)
    'follow for follow', 'f4f', 'sub4sub', 's4s',
    'like for like', 'l4l', 'view for view', 'v4v'
}

# Suspicious URL patterns
SUSPICIOUS_URL_PATTERNS = [
    r'bit\.ly',
    r'tinyurl',
    r'goo\.gl',
    r't\.co',
    r'ow\.ly',
    r'is\.gd',
    r'buff\.ly',
    r'discord\.gg',
    r'twitch\.tv/(?![\w]+$)',  # Non-standard Twitch URLs
    r'\d+\.\d+\.\d+\.\d+',    # IP addresses
    r'[a-z0-9]+\.(tk|ml|ga|cf)',  # Free domains
]

# Common substitution patterns for spam evasion
SPAM_SUBSTITUTION_PATTERNS = {
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
    '_': '',
    '-': '',
    '.': '',
    ' ': '',
}

class SpamDetectionFilter:
    """Main spam detection filter class"""
    
    def __init__(self):
        self.rules_table = None
        self.community_table = None
        try:
            self.rules_table = dynamodb.Table('waddlebot_spam_rules')
            self.community_table = dynamodb.Table('waddlebot_spam_settings')
        except Exception as e:
            logger.warning(f"DynamoDB tables not available: {e}")
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for better spam detection"""
        # Convert to lowercase
        text = text.lower()
        
        # Replace common substitutions
        for char, replacement in SPAM_SUBSTITUTION_PATTERNS.items():
            text = text.replace(char, replacement)
        
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def get_community_spam_rules(self, community_id: str) -> Tuple[Set[str], Set[str]]:
        """Get community-specific spam patterns and whitelist"""
        spam_patterns = set()
        whitelist = set()
        
        if not self.rules_table:
            return spam_patterns, whitelist
        
        try:
            # Get community-specific rules
            response = self.rules_table.query(
                KeyConditionExpression=Key('community_id').eq(community_id)
            )
            
            for item in response.get('Items', []):
                pattern = item.get('pattern', '').lower()
                if item.get('action') == 'block':
                    spam_patterns.add(pattern)
                elif item.get('action') == 'allow':
                    whitelist.add(pattern)
            
            # Check if community uses default patterns
            if self.community_table:
                settings = self.community_table.get_item(
                    Key={'community_id': community_id}
                ).get('Item', {})
                
                if settings.get('use_default_patterns', True):
                    spam_patterns.update(DEFAULT_SPAM_PATTERNS)
        
        except Exception as e:
            logger.error(f"Error fetching community spam rules: {e}")
            # Fall back to defaults
            spam_patterns.update(DEFAULT_SPAM_PATTERNS)
        
        return spam_patterns, whitelist
    
    def check_suspicious_urls(self, message: str) -> List[str]:
        """Check for suspicious URL patterns"""
        found_urls = []
        
        for pattern in SUSPICIOUS_URL_PATTERNS:
            matches = re.findall(pattern, message, re.IGNORECASE)
            if matches:
                found_urls.extend(matches)
        
        return found_urls
    
    def check_repetitive_content(self, message: str) -> Dict:
        """Check for repetitive or caps-heavy content"""
        issues = []
        
        # Check for excessive caps
        if len(message) > 10:
            caps_ratio = sum(1 for c in message if c.isupper()) / len(message)
            if caps_ratio > 0.7:
                issues.append('excessive_caps')
        
        # Check for repeated characters
        repeated_chars = re.findall(r'(.)\1{4,}', message)
        if repeated_chars:
            issues.append('repeated_characters')
        
        # Check for repeated words/phrases
        words = message.lower().split()
        if len(words) > 3:
            unique_words = set(words)
            repetition_ratio = (len(words) - len(unique_words)) / len(words)
            if repetition_ratio > 0.5:
                issues.append('repeated_words')
        
        return {
            'has_issues': len(issues) > 0,
            'issues': issues,
            'caps_heavy': 'excessive_caps' in issues,
            'repetitive': any(issue in ['repeated_characters', 'repeated_words'] for issue in issues)
        }
    
    def calculate_spam_score(self, message: str, community_id: str) -> Dict:
        """Calculate comprehensive spam score"""
        original_message = message
        normalized_message = self.normalize_text(message)
        
        # Get community-specific patterns
        spam_patterns, whitelist = self.get_community_spam_rules(community_id)
        
        # Check for spam patterns
        found_patterns = []
        confidence = 0
        
        # Check each spam pattern
        for pattern in spam_patterns:
            normalized_pattern = self.normalize_text(pattern)
            if normalized_pattern in normalized_message:
                # Skip if whitelisted
                if any(self.normalize_text(allowed) in normalized_message for allowed in whitelist):
                    continue
                
                found_patterns.append(pattern)
                # Higher confidence for exact matches
                if pattern in message.lower():
                    confidence += 15
                else:
                    confidence += 10
        
        # Check for suspicious URLs
        suspicious_urls = self.check_suspicious_urls(message)
        if suspicious_urls:
            found_patterns.extend([f"suspicious_url:{url}" for url in suspicious_urls])
            confidence += len(suspicious_urls) * 20
        
        # Check repetitive content
        repetitive_check = self.check_repetitive_content(message)
        if repetitive_check['has_issues']:
            found_patterns.extend([f"repetitive:{issue}" for issue in repetitive_check['issues']])
            confidence += len(repetitive_check['issues']) * 8
        
        # Determine severity and action
        severity = 'clean'
        action = 'pass'
        
        if confidence >= 50:
            severity = 'high'
            action = 'block'
        elif confidence >= 30:
            severity = 'moderate'
            action = 'warn'
        elif confidence >= 15:
            severity = 'low'
            action = 'flag'
        
        return {
            'original': original_message,
            'spam_score': confidence,
            'patterns': found_patterns,
            'suspicious_urls': suspicious_urls,
            'repetitive_issues': repetitive_check,
            'severity': severity,
            'action': action,
            'clean': confidence < 15
        }

def lambda_handler(event, context):
    """
    Lambda handler for spam detection module
    Expected event format:
    {
        "session_id": "uuid",
        "community_id": "community_identifier",
        "entity_id": "platform:server:channel",
        "user_id": "user_identifier",
        "user_name": "username",
        "message": "message content",
        "platform": "discord/twitch/slack",
        "action": "check/add_pattern/remove_pattern/get_settings"
    }
    """
    
    try:
        # Parse the event
        if isinstance(event, str):
            event = json.loads(event)
        
        action = event.get('action', 'check')
        filter = SpamDetectionFilter()
        
        if action == 'check':
            # Check message for spam
            message = event.get('message', '')
            community_id = event.get('community_id', 'default')
            
            if not message:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'No message provided'})
                }
            
            result = filter.calculate_spam_score(message, community_id)
            
            # Log if spam detected
            if not result['clean']:
                logger.info(f"Spam detected in community {community_id}: score={result['spam_score']}, patterns={result['patterns']}")
            
            # Prepare response for router
            response = {
                'session_id': event.get('session_id'),
                'success': True,
                'response_action': 'moderation',
                'response_data': {
                    'original_message': result['original'],
                    'clean': result['clean'],
                    'spam_score': result['spam_score'],
                    'patterns': result['patterns'],
                    'suspicious_urls': result['suspicious_urls'],
                    'repetitive_issues': result['repetitive_issues'],
                    'severity': result['severity'],
                    'suggested_action': result['action']
                },
                'module_name': 'spam_detection_module',
                'processing_time_ms': 15
            }
            
            # Add chat response based on action
            if result['action'] == 'block':
                response['chat_message'] = f"🚫 Message blocked - spam detected."
            elif result['action'] == 'warn':
                response['chat_message'] = f"⚠️ Warning: Your message appears to contain promotional content."
            elif result['action'] == 'flag':
                # Don't send user message for flags, just log for mods
                pass
            
            return {
                'statusCode': 200,
                'body': json.dumps(response)
            }
        
        elif action == 'add_pattern':
            # Add spam pattern to community's list (admin only)
            community_id = event.get('community_id')
            pattern = event.get('pattern', '').lower()
            pattern_action = event.get('pattern_action', 'block')  # block or allow
            added_by = event.get('user_name', 'admin')
            
            if not community_id or not pattern:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Missing community_id or pattern'})
                }
            
            # Add to DynamoDB
            if filter.rules_table:
                filter.rules_table.put_item(Item={
                    'community_id': community_id,
                    'pattern': pattern,
                    'action': pattern_action,
                    'added_by': added_by,
                    'added_at': datetime.utcnow().isoformat()
                })
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'message': f"Spam pattern '{pattern}' added to {pattern_action} list"
                })
            }
        
        elif action == 'remove_pattern':
            # Remove pattern from community's list (admin only)
            community_id = event.get('community_id')
            pattern = event.get('pattern', '').lower()
            
            if not community_id or not pattern:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Missing community_id or pattern'})
                }
            
            # Remove from DynamoDB
            if filter.rules_table:
                filter.rules_table.delete_item(
                    Key={
                        'community_id': community_id,
                        'pattern': pattern
                    }
                )
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'message': f"Spam pattern '{pattern}' removed"
                })
            }
        
        elif action == 'get_settings':
            # Get community spam settings
            community_id = event.get('community_id')
            
            if not community_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Missing community_id'})
                }
            
            spam_patterns, whitelist = filter.get_community_spam_rules(community_id)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'spam_patterns': list(spam_patterns),
                    'whitelist_patterns': list(whitelist),
                    'default_patterns_count': len(DEFAULT_SPAM_PATTERNS),
                    'uses_defaults': True  # TODO: Get from community settings
                })
            }
        
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Unknown action: {action}'})
            }
    
    except Exception as e:
        logger.error(f"Error in spam detection module: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'session_id': event.get('session_id')
            })
        }