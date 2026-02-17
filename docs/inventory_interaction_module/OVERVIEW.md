# Inventory Interaction Module - Overview

## Module Purpose

The **Inventory Interaction Module** (WaddleBot Quartermaster System) is a comprehensive inventory management system for WaddleBot communities. It provides complete CRUD operations, checkout/checkin workflows, full-text search capabilities, and comprehensive audit logging for tracking any inventory item—whether physical equipment, consumables, or in-game assets.

This module enables communities to manage shared resources efficiently with features like stock tracking, checkout pricing in community currency, due date management, and detailed audit trails.

## Quick Reference

| Property | Value |
|----------|-------|
| **Source Path** | `/home/penguin/code/waddlebot/action/interactive/inventory_interaction_module/` |
| **Language** | Python 3.12 |
| **Framework** | Quart (async Python web framework) |
| **Module Port** | 8024 |
| **Module Version** | 2.0.0 |
| **Service Version** | 1.0.0 |
| **Database** | PostgreSQL |
| **Async Pattern** | AsyncDAL (non-blocking database operations) |
| **Key Service** | `InventoryService` in `services/inventory_service.py` |

## Key Capabilities

### Item Management
- **CRUD Operations**: Create, read, update, delete inventory items
- **Stock Tracking**: Manage quantities with add/remove operations
- **Metadata Support**: Store custom properties per item
- **Soft Deletes**: Safe deletion with audit trail preservation

### Checkout System
- **Check Out**: Reserve items with configurable duration
- **Check In**: Return items with condition tracking
- **Due Date Management**: Automatic calculation and tracking
- **Overdue Detection**: Identify items past return deadline
- **Quantity Support**: Check out/return multiple units

### Search & Discovery
- **Full-Text Search**: PostgreSQL GIN index-based search across name, description, category, type
- **Category Filtering**: Filter items by category with availability options
- **Type Filtering**: Filter by item type (equipment, consumable, collectible)
- **Availability Status**: Get items with stock availability
- **Low Stock Detection**: Identify items with limited availability

### Audit & Compliance
- **Immutable Audit Trail**: Complete log of all operations
- **Action Tracking**: Logs checkout, return, add_stock, remove_stock, update, delete
- **User Attribution**: Track who performed each action
- **Quantity Changes**: Record all stock adjustments
- **Detailed Context**: Store operation details (notes, duration, condition)

### Reporting
- **Inventory Summary**: Get comprehensive statistics (total items, quantities, available, active checkouts, overdue, low stock)
- **Active Checkouts**: Monitor currently borrowed items
- **Overdue Checkouts**: Track items past due date
- **User History**: View user's complete checkout history
- **Audit Reports**: Generate audit logs filtered by item, user, or action

## Documentation Index

| Document | Purpose |
|----------|---------|
| **OVERVIEW.md** | This file - module purpose, capabilities, quick reference |
| **USAGE.md** | Getting started, Docker setup, health checks, common workflows |
| **API.md** | Complete endpoint reference, request/response examples, error handling |
| **ARCHITECTURE.md** | Internal components, data flow, service structure, dependencies |
| **CONFIGURATION.md** | Environment variables, required/optional settings, example .env file |
| **TESTING.md** | Test strategy, test data, running tests, validation procedures |
| **TROUBLESHOOTING.md** | Common errors, debug steps, logs, solutions |
| **RELEASE_NOTES.md** | Version history and release documentation |

## Core Components

### Main Application (`app.py`)
- Quart async web application
- Health/metrics blueprint registration
- Hypercorn ASGI server (4 workers)
- AsyncDAL database initialization
- API v1 blueprint with `/api/v1/status` endpoint

### Configuration (`config.py`)
- Module name and version management
- Port and database URL configuration
- Core API integration endpoints
- Logging setup and levels
- Redis credential listener for secure token management
- Environment variable loading with fallbacks

### Inventory Service (`services/inventory_service.py`)
- **InventoryService class**: Main service with all business logic
- **CRUD Methods**: `add_item()`, `get_item()`, `update_item()`, `delete_item()`
- **Checkout Methods**: `checkout_item()`, `checkin_item()`, `get_active_checkouts()`, `get_overdue_checkouts()`, `get_user_checkouts()`
- **Stock Methods**: `add_stock()`, `remove_stock()`
- **Search Methods**: `search_items()`, `get_items_by_category()`, `get_items_by_type()`, `get_available_items()`, `get_low_stock_items()`
- **Reporting Methods**: `get_inventory_summary()`, `get_audit_log()`
- **Internal Methods**: `_log_action()` for audit trail

## Data Models

### Inventory Item
```python
{
    'id': int,
    'community_id': int,
    'name': str,
    'description': str,
    'item_type': str,  # equipment, consumable, collectible, etc.
    'category': str,
    'quantity': int,  # Total in inventory
    'available_quantity': int,  # Available for checkout
    'checkout_price': int,  # Community currency cost
    'max_checkout_duration_hours': int,
    'image_url': str,
    'metadata': dict,  # Custom fields
    'created_at': datetime,
    'updated_at': datetime,
    'deleted_at': datetime  # Null unless soft deleted
}
```

### Checkout Record
```python
{
    'id': int,
    'item_id': int,
    'user_id': int,
    'quantity': int,
    'checked_out_at': datetime,
    'due_at': datetime,
    'returned_at': datetime,
    'returned_condition': str,
    'status': str,  # 'active', 'returned', 'overdue'
    'notes': str
}
```

### Audit Log Entry
```python
{
    'id': int,
    'item_id': int,
    'user_id': int,
    'community_id': int,
    'action': str,  # checkout, return, add_stock, remove_stock, update, delete
    'quantity_change': int,
    'details': dict,  # Additional context
    'created_at': datetime
}
```

## Database Tables

The module requires three main tables (created by migration 014):

| Table | Purpose | Records |
|-------|---------|---------|
| `inventory_items` | Item catalog with stock levels | Items per community |
| `inventory_checkouts` | Checkout/return records | Checkout history |
| `inventory_log` | Immutable audit trail | All operations |

### Key Indexes
- `idx_inventory_items_community`: Community lookups (fast filtering)
- `idx_inventory_items_active`: Recent items (created_at DESC)
- `idx_inventory_items_category`: Category/type filtering
- `idx_inventory_items_stock`: Low stock queries
- `idx_inventory_items_search`: Full-text search (GIN index)
- `idx_inventory_checkouts_active`: Active/overdue tracking
- `idx_inventory_checkouts_item`: Item-specific history
- `idx_inventory_checkouts_user`: User history lookups
- `idx_inventory_log_*`: Audit trail queries

## Technology Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.12 | Runtime |
| Quart | 0.19.0+ | Async web framework |
| Hypercorn | 0.16.0+ | ASGI server |
| PostgreSQL | 13+ | Database |
| AsyncDAL | Latest | Non-blocking DB access |
| httpx | 0.27.0 | HTTP client for API calls |
| python-dotenv | 1.0.0+ | Environment configuration |

## Deployment Information

### Container Details
- **Image**: `waddlebot/inventory-interaction:latest`
- **Base Image**: `python:3.12-slim`
- **Port Exposed**: 8024
- **Workers**: 4 (Hypercorn)
- **Non-Root User**: `waddlebot:waddlebot`
- **Log Directory**: `/var/log/waddlebotlog`

### Environment Requirements
- PostgreSQL database with migration 014 applied
- Redis (optional, for credential notifications)
- Core API service for integration
- Router service for API communications

## Features Highlight

### 🔒 Security & Compliance
- Immutable audit logging of all operations
- User attribution for every change
- Soft deletes preserve audit trail
- Role-based access control integration
- Community-scoped operations

### ⚡ Performance Optimizations
- AsyncDAL for non-blocking database operations
- Connection pooling with configurable pool size
- PostgreSQL GIN index for full-text search
- Strategic database indexes for fast queries
- Async/await throughout codebase

### 📊 Analytics Ready
- Complete audit trail for compliance reporting
- Inventory summary statistics
- User checkout history tracking
- Low stock detection and alerting
- Overdue tracking for follow-ups

### 🔄 Integration Ready
- Community currency integration support
- Notification system hooks
- Reporting service integration
- REST API design for easy integration
- Metadata field for custom integrations

## Common Use Cases

1. **Equipment Library**: Manage shared laptops, cameras, microphones, lighting rigs
2. **Game Items**: Track in-game inventory, loot, collectibles
3. **Supply Management**: Monitor consumables, parts, materials
4. **Resource Booking**: Schedule equipment access with due dates
5. **Member Access**: Control who can borrow what items
6. **Compliance Tracking**: Maintain audit trail of all transactions

## Getting Started

### Quick Start Steps
1. Read [USAGE.md](USAGE.md) for setup and Docker instructions
2. Check [CONFIGURATION.md](CONFIGURATION.md) for environment variables
3. Review [API.md](API.md) for endpoint details
4. Explore [EXAMPLES.py](../../action/interactive/inventory_interaction_module/EXAMPLES.py) for real-world patterns
5. Refer to [TESTING.md](TESTING.md) for validation procedures

### Key Endpoints
- `GET /health` - Health check
- `GET /metrics` - Performance metrics
- `GET /api/v1/status` - Module status
- Service methods accessed programmatically through InventoryService

## Next Steps

- **Setup**: Go to [USAGE.md](USAGE.md) for installation and local setup
- **Integrate**: See [ARCHITECTURE.md](ARCHITECTURE.md) for integration patterns
- **Deploy**: Check [CONFIGURATION.md](CONFIGURATION.md) for production deployment
- **Troubleshoot**: Visit [TROUBLESHOOTING.md](TROUBLESHOOTING.md) if issues arise

---

**Module**: inventory_interaction_module  
**Version**: 2.0.0 (service: 1.0.0)  
**Language**: Python  
**Framework**: Quart  
**Database**: PostgreSQL  
**Port**: 8024
