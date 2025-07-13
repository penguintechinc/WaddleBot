"""
String matching service for content moderation and auto-responses
Handles string pattern matching when no direct command is found
"""

import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from ..models import db, db_read
from .cache_manager import CacheManager

logger = logging.getLogger(__name__)

@dataclass
class StringMatchResult:
    """String match result"""
    matched: bool
    action: str = None  # warn, block, command
    rule_id: int = None
    message: str = None
    command_to_execute: str = None
    command_parameters: List[str] = None
    priority: int = 999

class StringMatcher:
    """High-performance string matching with caching"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.compiled_regex_cache = {}  # Cache for compiled regex patterns
    
    async def check_string_match(self, message_content: str, entity_id: str) -> StringMatchResult:
        """Check if message content matches any string patterns for the entity"""
        try:
            # Get string match rules for this entity
            rules = await self.get_string_rules(entity_id)
            
            if not rules:
                return StringMatchResult(matched=False)
            
            # Check each rule in priority order (lower number = higher priority)
            for rule in sorted(rules, key=lambda x: x.get('priority', 100)):
                match_result = self.test_string_match(message_content, rule)
                
                if match_result.matched:
                    # Log the match
                    await self.log_string_match(rule['id'], entity_id, message_content)
                    return match_result
            
            return StringMatchResult(matched=False)
            
        except Exception as e:
            logger.error(f"Error checking string match: {str(e)}")
            return StringMatchResult(matched=False)
    
    def test_string_match(self, message_content: str, rule: Dict) -> StringMatchResult:
        """Test a message against a specific string rule"""
        try:
            pattern = rule['string']
            match_type = rule.get('match_type', 'exact')
            case_sensitive = rule.get('case_sensitive', False)
            
            # Prepare text for matching
            text = message_content if case_sensitive else message_content.lower()
            search_pattern = pattern if case_sensitive else pattern.lower()
            
            # Test based on match type
            matched = False
            
            # Special case: "*" matches all text
            if pattern == "*":
                matched = True
            elif match_type == 'exact':
                matched = text == search_pattern
            elif match_type == 'contains':
                matched = search_pattern in text
            elif match_type == 'word':
                # Word boundary matching
                word_pattern = r'\b' + re.escape(search_pattern) + r'\b'
                matched = bool(re.search(word_pattern, text, re.IGNORECASE if not case_sensitive else 0))
            elif match_type == 'regex':
                # Regex matching with caching
                try:
                    regex_key = f"{pattern}_{case_sensitive}"
                    if regex_key not in self.compiled_regex_cache:
                        flags = 0 if case_sensitive else re.IGNORECASE
                        self.compiled_regex_cache[regex_key] = re.compile(pattern, flags)
                    
                    regex = self.compiled_regex_cache[regex_key]
                    matched = bool(regex.search(text))
                except re.error as e:
                    logger.error(f"Invalid regex pattern '{pattern}': {str(e)}")
                    return StringMatchResult(matched=False)
            
            if matched:
                return StringMatchResult(
                    matched=True,
                    action=rule['action'],
                    rule_id=rule['id'],
                    message=self.get_action_message(rule),
                    command_to_execute=rule.get('command_to_execute'),
                    command_parameters=rule.get('command_parameters', []),
                    priority=rule.get('priority', 100)
                )
            else:
                return StringMatchResult(matched=False)
                
        except Exception as e:
            logger.error(f"Error testing string match: {str(e)}")
            return StringMatchResult(matched=False)
    
    def get_action_message(self, rule: Dict) -> str:
        """Get the appropriate message for the rule action"""
        action = rule['action']
        
        if action == 'warn':
            return rule.get('warning_message', 'Warning: Your message contains content that may violate community guidelines.')
        elif action == 'block':
            return rule.get('block_message', 'Your message has been blocked due to policy violations.')
        elif action == 'command':
            return f"Executing command: {rule.get('command_to_execute', 'unknown')}"
        elif action == 'webhook':
            return f"Sending to webhook: {rule.get('webhook_url', 'unknown')}"
        else:
            return f"Action triggered: {action}"
    
    async def get_string_rules(self, entity_id: str) -> List[Dict]:
        """Get string matching rules for an entity (with caching)"""
        cache_key = f"stringrules:{entity_id}"
        
        # Try cache first
        cached_rules = self.cache_manager.get(cache_key)
        if cached_rules is not None:
            return cached_rules
        
        try:
            # Query database for rules that apply to this entity
            rules = db_read(
                (db_read.stringmatch.is_active == True)
            ).select()
            
            # Filter rules that apply to this entity
            applicable_rules = []
            for rule in rules:
                enabled_entities = rule.enabled_entity_ids or []
                
                # Check if this entity is in the enabled list or if it's a global rule
                if not enabled_entities or entity_id in enabled_entities:
                    applicable_rules.append(dict(rule))
            
            # Cache the results
            self.cache_manager.set(cache_key, applicable_rules, ttl=300)  # 5 minute cache
            
            return applicable_rules
            
        except Exception as e:
            logger.error(f"Error getting string rules for entity {entity_id}: {str(e)}")
            return []
    
    async def log_string_match(self, rule_id: int, entity_id: str, message_content: str):
        """Log a string match occurrence"""
        try:
            # Update match count and last matched timestamp
            rule = db(db.stringmatch.id == rule_id).select().first()
            if rule:
                db.stringmatch[rule_id] = dict(
                    match_count=rule.match_count + 1,
                    last_matched=datetime.utcnow()
                )
                db.commit()
                
            # Optionally log to a separate match events table if detailed tracking is needed
            # This could be added later for audit purposes
            
        except Exception as e:
            logger.error(f"Error logging string match: {str(e)}")
    
    def clear_cache(self, entity_id: str = None):
        """Clear string rules cache"""
        if entity_id:
            cache_key = f"stringrules:{entity_id}"
            self.cache_manager.delete(cache_key)
        else:
            # Clear all string rule caches (would need implementation in cache_manager)
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get string matcher statistics"""
        try:
            total_rules = db(db.stringmatch.is_active == True).count()
            
            # Get rule breakdown by action
            warn_rules = db(
                (db.stringmatch.is_active == True) &
                (db.stringmatch.action == 'warn')
            ).count()
            
            block_rules = db(
                (db.stringmatch.is_active == True) &
                (db.stringmatch.action == 'block')
            ).count()
            
            command_rules = db(
                (db.stringmatch.is_active == True) &
                (db.stringmatch.action == 'command')
            ).count()
            
            # Get total matches
            total_matches = db().select(db.stringmatch.match_count.sum()).first()[db.stringmatch.match_count.sum()] or 0
            
            return {
                "total_rules": total_rules,
                "warn_rules": warn_rules,
                "block_rules": block_rules,
                "command_rules": command_rules,
                "total_matches": total_matches,
                "compiled_regex_cache_size": len(self.compiled_regex_cache)
            }
            
        except Exception as e:
            logger.error(f"Error getting string matcher stats: {str(e)}")
            return {}

# Global string matcher instance (will be initialized with cache manager)
string_matcher = None

def get_string_matcher(cache_manager: CacheManager) -> StringMatcher:
    """Get or create string matcher instance"""
    global string_matcher
    if string_matcher is None:
        string_matcher = StringMatcher(cache_manager)
    return string_matcher