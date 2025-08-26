"""
Chat Filter Service - Combined censorship, spam detection, and URL blocking
High-performance async implementation for handling thousands of messages per second
"""

import re
import json
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Set, Tuple, Union
from datetime import datetime
from urllib.parse import urlparse
from functools import lru_cache
import threading

from models import db
from config import Config

logger = logging.getLogger(__name__)

# Default banned words (from censorship module)
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
}

# Default spam patterns (from spam detection module)
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
    r'\d+\.\d+\.\d+\.\d+',    # IP addresses
    r'[a-z0-9]+\.(tk|ml|ga|cf)',  # Free domains
]

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
    '_': '',
    '-': '',
    '.': '',
}

class ChatFilterService:
    """Unified chat filtering service with high-performance async processing"""
    
    def __init__(self):
        self.db = db
        self.thread_pool = ThreadPoolExecutor(max_workers=Config.MAX_WORKERS)
        self.cache_lock = threading.RLock()
        self._settings_cache = {}
        self._words_cache = {}
        self._patterns_cache = {}
        self._url_settings_cache = {}
        
        # Compile regex patterns for better performance
        self._compiled_suspicious_urls = [re.compile(pattern, re.IGNORECASE) for pattern in SUSPICIOUS_URL_PATTERNS]
        self._compiled_url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE)
    
    @lru_cache(maxsize=1000)
    def normalize_text(self, text: str) -> str:
        """Normalize text for better pattern matching (cached for performance)"""
        text = text.lower()
        
        # Replace common substitutions
        for char, replacement in SUBSTITUTION_PATTERNS.items():
            text = text.replace(char, replacement)
        
        # Remove extra spaces and special characters
        text = re.sub(r'[^a-z0-9\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    async def check_message_async(self, message: str, community_id: str, user_id: str, platform: str) -> Dict:
        """Async comprehensive message filtering for high throughput"""
        loop = asyncio.get_event_loop()
        
        # Run CPU-intensive filtering in thread pool
        result = await loop.run_in_executor(
            self.thread_pool,
            self.check_message,
            message, community_id, user_id, platform
        )
        
        return result
    
    async def check_messages_batch(self, messages: List[Dict]) -> List[Dict]:
        """Process multiple messages concurrently"""
        tasks = []
        
        for msg_data in messages:
            task = self.check_message_async(
                msg_data['message'],
                msg_data['community_id'],
                msg_data['user_id'],
                msg_data.get('platform', 'unknown')
            )
            tasks.append(task)
        
        # Process all messages concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing message {i}: {result}")
                processed_results.append({
                    'original': messages[i]['message'],
                    'clean': True,
                    'error': str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_community_settings(self, community_id: str) -> Dict:
        """Get community filter settings with caching"""
        # Check cache first
        with self.cache_lock:
            if community_id in self._settings_cache:
                cached_time = self._settings_cache[community_id].get('cached_at', 0)
                if datetime.utcnow().timestamp() - cached_time < Config.CACHE_TTL:
                    return self._settings_cache[community_id]['data']
        
        if not self.db:
            return self._get_default_settings()
        
        try:
            settings = self.db((self.db.filter_settings.community_id == community_id)).select().first()
            if settings:
                result = {
                    'profanity_enabled': settings.profanity_enabled,
                    'spam_detection_enabled': settings.spam_detection_enabled,
                    'url_blocking_enabled': settings.url_blocking_enabled,
                    'use_default_profanity': settings.use_default_profanity,
                    'use_default_spam_patterns': settings.use_default_spam_patterns,
                    'severity_actions': json.loads(settings.severity_actions) if isinstance(settings.severity_actions, str) else settings.severity_actions,
                    'strike_policy': json.loads(settings.strike_policy) if isinstance(settings.strike_policy, str) else settings.strike_policy,
                    'auto_timeout': settings.auto_timeout,
                    'timeout_duration': settings.timeout_duration
                }
            else:
                result = self._get_default_settings()
            
            # Cache the result
            with self.cache_lock:
                self._settings_cache[community_id] = {
                    'data': result,
                    'cached_at': datetime.utcnow().timestamp()
                }
            
            return result
        except Exception as e:
            logger.error(f"Error getting community settings: {e}")
            return self._get_default_settings()
    
    def _get_default_settings(self) -> Dict:
        """Get default filter settings"""
        return {
            'profanity_enabled': Config.ENABLE_PROFANITY_FILTER,
            'spam_detection_enabled': Config.ENABLE_SPAM_DETECTION,
            'url_blocking_enabled': Config.ENABLE_URL_BLOCKING,
            'use_default_profanity': True,
            'use_default_spam_patterns': True,
            'severity_actions': {'mild': 'warn', 'moderate': 'censor', 'severe': 'block'},
            'strike_policy': {'strikes': 3, 'action': 'timeout', 'duration': 300},
            'auto_timeout': False,
            'timeout_duration': 300
        }
    
    def get_community_words(self, community_id: str) -> Tuple[Set[str], Set[str]]:
        """Get community-specific banned and allowed words"""
        banned = set()
        allowed = set()
        
        if not self.db:
            return banned, allowed
        
        try:
            # Get community-specific words
            words = self.db((self.db.censorship_words.community_id == community_id)).select()
            
            for word in words:
                if word.action == 'ban':
                    banned.add(word.word.lower())
                elif word.action == 'allow':
                    allowed.add(word.word.lower())
            
            # Check if community uses default list
            settings = self.get_community_settings(community_id)
            if settings.get('use_default_profanity', True):
                banned.update(DEFAULT_BANNED_WORDS)
        
        except Exception as e:
            logger.error(f"Error fetching community words: {e}")
            # Fall back to defaults
            banned.update(DEFAULT_BANNED_WORDS)
        
        return banned, allowed
    
    def get_community_spam_patterns(self, community_id: str) -> Tuple[Set[str], Set[str]]:
        """Get community-specific spam patterns and whitelist"""
        patterns = set()
        whitelist = set()
        
        if not self.db:
            return patterns, whitelist
        
        try:
            # Get community-specific patterns
            spam_patterns = self.db((self.db.spam_patterns.community_id == community_id)).select()
            
            for pattern in spam_patterns:
                if pattern.action == 'block':
                    patterns.add(pattern.pattern.lower())
                elif pattern.action == 'allow':
                    whitelist.add(pattern.pattern.lower())
            
            # Check if community uses default patterns
            settings = self.get_community_settings(community_id)
            if settings.get('use_default_spam_patterns', True):
                patterns.update(DEFAULT_SPAM_PATTERNS)
        
        except Exception as e:
            logger.error(f"Error fetching community spam patterns: {e}")
            # Fall back to defaults
            patterns.update(DEFAULT_SPAM_PATTERNS)
        
        return patterns, whitelist
    
    def get_url_settings(self, community_id: str) -> Dict:
        """Get community URL blocking settings"""
        if not self.db:
            return {
                'url_blocking_enabled': False,
                'allow_all_urls': True,
                'allowed_domains': Config.TRUSTED_DOMAINS,
                'blocked_domains': []
            }
        
        try:
            settings = self.db((self.db.url_settings.community_id == community_id)).select().first()
            if settings:
                return {
                    'url_blocking_enabled': settings.url_blocking_enabled,
                    'allow_all_urls': settings.allow_all_urls,
                    'allowed_domains': json.loads(settings.allowed_domains) if isinstance(settings.allowed_domains, str) else settings.allowed_domains,
                    'blocked_domains': json.loads(settings.blocked_domains) if isinstance(settings.blocked_domains, str) else settings.blocked_domains,
                    'require_https': settings.require_https,
                    'block_ip_addresses': settings.block_ip_addresses,
                    'block_shorteners': settings.block_shorteners,
                    'trusted_shorteners': json.loads(settings.trusted_shorteners) if isinstance(settings.trusted_shorteners, str) else settings.trusted_shorteners
                }
            else:
                return {
                    'url_blocking_enabled': False,
                    'allow_all_urls': True,
                    'allowed_domains': Config.TRUSTED_DOMAINS,
                    'blocked_domains': [],
                    'require_https': False,
                    'block_ip_addresses': True,
                    'block_shorteners': True,
                    'trusted_shorteners': Config.TRUSTED_SHORTENERS
                }
        except Exception as e:
            logger.error(f"Error getting URL settings: {e}")
            return {'url_blocking_enabled': False, 'allow_all_urls': True, 'allowed_domains': [], 'blocked_domains': []}
    
    def check_profanity(self, message: str, community_id: str) -> Dict:
        """Check message for profanity"""
        normalized_message = self.normalize_text(message)
        banned_words, allowed_words = self.get_community_words(community_id)
        
        found_violations = []
        severity = 'clean'
        
        # Check words and phrases
        words_to_check = set()
        words_to_check.update(normalized_message.split())
        
        # Add bigrams
        words = normalized_message.split()
        for i in range(len(words) - 1):
            words_to_check.add(f"{words[i]} {words[i+1]}")
        
        # Check against banned words
        for word in words_to_check:
            if word in allowed_words:
                continue
            
            for banned in banned_words:
                normalized_banned = self.normalize_text(banned)
                if normalized_banned in word or word in normalized_banned:
                    found_violations.append(banned)
                    
                    # Determine severity
                    if any(slur in banned.lower() for slur in ['n*gg', 'f*g', 'r*tard', 'tr*nny']):
                        severity = 'severe'
                    elif severity != 'severe':
                        severity = 'moderate'
        
        # Generate censored version
        censored_message = self._censor_message(message, found_violations)
        
        return {
            'has_profanity': len(found_violations) > 0,
            'violations': found_violations,
            'severity': severity,
            'censored': censored_message
        }
    
    def check_spam(self, message: str, community_id: str) -> Dict:
        """Check message for spam patterns"""
        normalized_message = self.normalize_text(message)
        spam_patterns, whitelist = self.get_community_spam_patterns(community_id)
        
        found_patterns = []
        confidence = 0
        
        # Check spam patterns
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
        suspicious_urls = self._check_suspicious_urls(message)
        if suspicious_urls:
            found_patterns.extend([f"suspicious_url:{url}" for url in suspicious_urls])
            confidence += len(suspicious_urls) * 20
        
        # Check repetitive content
        repetitive_check = self._check_repetitive_content(message)
        if repetitive_check['has_issues']:
            found_patterns.extend([f"repetitive:{issue}" for issue in repetitive_check['issues']])
            confidence += len(repetitive_check['issues']) * 8
        
        return {
            'is_spam': confidence >= Config.SPAM_CONFIDENCE_THRESHOLD,
            'spam_score': confidence,
            'patterns': found_patterns,
            'suspicious_urls': suspicious_urls,
            'repetitive_issues': repetitive_check
        }
    
    def check_urls(self, message: str, community_id: str) -> Dict:
        """Check message for blocked URLs"""
        url_settings = self.get_url_settings(community_id)
        
        if not url_settings.get('url_blocking_enabled', False):
            return {'has_blocked_urls': False, 'blocked_urls': [], 'allowed_urls': []}
        
        # Extract URLs from message
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, message, re.IGNORECASE)
        
        blocked_urls = []
        allowed_urls = []
        
        for url in urls:
            if self._is_url_blocked(url, url_settings):
                blocked_urls.append(url)
            else:
                allowed_urls.append(url)
        
        return {
            'has_blocked_urls': len(blocked_urls) > 0,
            'blocked_urls': blocked_urls,
            'allowed_urls': allowed_urls
        }
    
    def check_message(self, message: str, community_id: str, user_id: str, platform: str) -> Dict:
        """Comprehensive message filtering"""
        settings = self.get_community_settings(community_id)
        
        # Initialize results
        result = {
            'original': message,
            'clean': True,
            'filter_type': 'none',
            'severity': 'clean',
            'action': 'pass'
        }
        
        # Check if user is whitelisted
        if self._is_user_whitelisted(user_id, community_id):
            return result
        
        # Check profanity
        profanity_result = {}
        if settings.get('profanity_enabled', True):
            profanity_result = self.check_profanity(message, community_id)
            if profanity_result['has_profanity']:
                result.update({
                    'clean': False,
                    'filter_type': 'profanity',
                    'violations': profanity_result['violations'],
                    'censored': profanity_result['censored'],
                    'severity': profanity_result['severity']
                })
        
        # Check spam
        spam_result = {}
        if settings.get('spam_detection_enabled', True):
            spam_result = self.check_spam(message, community_id)
            if spam_result['is_spam']:
                if result['clean'] or spam_result['spam_score'] > 50:  # Override if higher severity
                    result.update({
                        'clean': False,
                        'filter_type': 'spam' if result['clean'] else 'combined',
                        'spam_score': spam_result['spam_score'],
                        'patterns': spam_result['patterns'],
                        'suspicious_urls': spam_result.get('suspicious_urls', []),
                        'severity': 'high' if spam_result['spam_score'] >= 50 else 'moderate'
                    })
        
        # Check URLs
        url_result = {}
        if settings.get('url_blocking_enabled', False):
            url_result = self.check_urls(message, community_id)
            if url_result['has_blocked_urls']:
                if result['clean'] or len(url_result['blocked_urls']) > 0:
                    result.update({
                        'clean': False,
                        'filter_type': 'url' if result['clean'] else 'combined',
                        'blocked_urls': url_result['blocked_urls'],
                        'severity': 'moderate'
                    })
        
        # Determine action based on severity and settings
        severity_actions = settings.get('severity_actions', {'mild': 'warn', 'moderate': 'censor', 'severe': 'block'})
        if not result['clean']:
            result['action'] = severity_actions.get(result['severity'], 'warn')
        
        # Log violation if enabled
        if not result['clean'] and settings.get('log_violations', True):
            self._log_violation(community_id, user_id, platform, result)
        
        return result
    
    def _check_suspicious_urls(self, message: str) -> List[str]:
        """Check for suspicious URL patterns"""
        found_urls = []
        
        for pattern in SUSPICIOUS_URL_PATTERNS:
            matches = re.findall(pattern, message, re.IGNORECASE)
            if matches:
                found_urls.extend(matches)
        
        return found_urls
    
    def _check_repetitive_content(self, message: str) -> Dict:
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
        
        # Check for repeated words
        words = message.lower().split()
        if len(words) > 3:
            unique_words = set(words)
            repetition_ratio = (len(words) - len(unique_words)) / len(words)
            if repetition_ratio > 0.5:
                issues.append('repeated_words')
        
        return {
            'has_issues': len(issues) > 0,
            'issues': issues
        }
    
    def _is_url_blocked(self, url: str, url_settings: Dict) -> bool:
        """Check if URL should be blocked"""
        if url_settings.get('allow_all_urls', True):
            return False
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Check if HTTPS required
            if url_settings.get('require_https', False) and parsed.scheme != 'https':
                return True
            
            # Check if IP address
            if url_settings.get('block_ip_addresses', True):
                if re.match(r'^\d+\.\d+\.\d+\.\d+', domain):
                    return True
            
            # Check blocked domains
            blocked_domains = url_settings.get('blocked_domains', [])
            if any(blocked in domain for blocked in blocked_domains):
                return True
            
            # Check allowed domains
            allowed_domains = url_settings.get('allowed_domains', [])
            if allowed_domains and not any(allowed in domain for allowed in allowed_domains):
                return True
            
            # Check shorteners
            if url_settings.get('block_shorteners', True):
                trusted_shorteners = url_settings.get('trusted_shorteners', [])
                shortener_patterns = ['bit.ly', 'tinyurl', 'goo.gl', 't.co', 'ow.ly', 'is.gd']
                
                for shortener in shortener_patterns:
                    if shortener in domain and shortener not in trusted_shorteners:
                        return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error checking URL {url}: {e}")
            return True  # Block on error to be safe
    
    def _is_user_whitelisted(self, user_id: str, community_id: str) -> bool:
        """Check if user is whitelisted"""
        if not self.db:
            return False
        
        try:
            whitelist_entry = self.db(
                (self.db.filter_whitelist.community_id == community_id) &
                (self.db.filter_whitelist.user_id == user_id) &
                ((self.db.filter_whitelist.expires_at == None) | 
                 (self.db.filter_whitelist.expires_at > datetime.utcnow()))
            ).select().first()
            
            return whitelist_entry is not None
        except Exception as e:
            logger.error(f"Error checking whitelist: {e}")
            return False
    
    def _censor_message(self, message: str, violations: List[str]) -> str:
        """Replace violations with asterisks"""
        censored = message
        
        for violation in violations:
            pattern = re.compile(re.escape(violation), re.IGNORECASE)
            if len(violation) > 2:
                replacement = violation[0] + '*' * (len(violation) - 2) + violation[-1]
            else:
                replacement = '*' * len(violation)
            censored = pattern.sub(replacement, censored)
        
        return censored
    
    def _log_violation(self, community_id: str, user_id: str, platform: str, result: Dict):
        """Log filter violation to database"""
        if not self.db:
            return
        
        try:
            self.db.filter_violations.insert(
                community_id=community_id,
                user_id=user_id,
                platform=platform,
                original_message=result['original'],
                censored_message=result.get('censored', result['original']),
                filter_type=result['filter_type'],
                violations=json.dumps(result.get('violations', [])),
                spam_score=result.get('spam_score', 0),
                severity=result['severity'],
                action_taken=result['action']
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Error logging violation: {e}")
    
    def get_filter_stats(self, community_id: Optional[str] = None) -> Dict:
        """Get filtering statistics"""
        if not self.db:
            return {'total_checks': 0, 'violations': 0}
        
        try:
            if community_id:
                violations = self.db((self.db.filter_violations.community_id == community_id)).select()
            else:
                violations = self.db(self.db.filter_violations).select()
            
            stats = {
                'total_violations': len(violations),
                'profanity_violations': len([v for v in violations if 'profanity' in v.filter_type]),
                'spam_violations': len([v for v in violations if 'spam' in v.filter_type]),
                'url_violations': len([v for v in violations if 'url' in v.filter_type]),
                'combined_violations': len([v for v in violations if v.filter_type == 'combined']),
                'actions': {
                    'warned': len([v for v in violations if v.action_taken == 'warn']),
                    'censored': len([v for v in violations if v.action_taken == 'censor']),
                    'blocked': len([v for v in violations if v.action_taken == 'block'])
                }
            }
            
            return stats
        except Exception as e:
            logger.error(f"Error getting filter stats: {e}")
            return {'total_violations': 0}