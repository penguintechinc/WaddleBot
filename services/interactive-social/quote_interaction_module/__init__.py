"""
Quote Interaction Module

Manages community quotes with full-text search and pagination support.
Uses migration 015 (quotes table with PostgreSQL full-text search tsvector).
"""

__version__ = '1.0.0'
__author__ = 'WaddleBot Team'
__all__ = ['quote_service', 'app', 'config']
