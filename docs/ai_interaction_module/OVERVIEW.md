# AI Interaction Module

> A Quart-based microservice that provides intelligent, context-aware chat responses for streaming communities with support for multiple pluggable AI provider backends including Ollama and WaddleAI.

## Purpose

The AI Interaction Module enables real-time, intelligent conversation in Waddles communities by integrating with multiple AI providers. It handles the complexity of provider management (Ollama for local models, WaddleAI for cloud-hosted OpenAI/Claude/MCP models) while exposing a simple REST and gRPC interface to the Router and other modules.

The module caches responses to reduce latency for commonly-asked questions and manages provider failover when services become unavailable. It supports request validation, provider health checks, and detailed error reporting to help developers understand why responses failed. The module is designed to be stateless and scalable, with each instance operating independently via shared Redis caching.

This module is critical for community engagement—nearly every interactive conversation in Waddles passes through the AI Interaction Module, making performance and reliability essential for user experience.

## Key Capabilities

- **Multiple AI Providers**: Seamless support for Ollama (local) and WaddleAI (cloud proxy for OpenAI, Claude, MCP, etc.)
- **Response Caching**: Redis-backed caching to reduce latency for frequent queries
- **Health Checking**: Continuous monitoring of AI provider health with automatic failover
- **Request Validation**: Validates input formats, token limits, and community permissions
- **Streaming Support**: Handles both request-response and streaming response patterns
- **Provider Configuration**: Hot-swappable provider selection without module restart
- **Detailed Error Reporting**: Clear error messages identifying provider, request, or system issues
- **Performance Metrics**: Tracks response times, cache hit rates, and provider reliability

## Documentation Index

| Document | Description |
|---|---|
| [USAGE.md](USAGE.md) | Getting started, running locally, common workflows |
| [API.md](API.md) | Endpoints, request/response formats, error codes |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Internal design, data flows, component breakdown |
| [CONFIGURATION.md](CONFIGURATION.md) | Environment variables, setup, feature flags |
| [TESTING.md](TESTING.md) | Test strategy, mock data, how to run tests |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common issues, debug steps, FAQ |
| [RELEASE_NOTES.md](RELEASE_NOTES.md) | Version history, migrations |

## Quick Reference

| Item | Value |
|---|---|
| Source | `action/interactive/ai_interaction_module/` |
| Language | Python 3.13 |
| Framework | Quart (async Flask) |
| Port | 8005 |
| Maintained by | Penguin Tech Inc |
