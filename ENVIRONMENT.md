# Environment & API Key Guide

This guide details all environment variables, security measures, and instructions for obtaining test and production API credentials for **سync**.

## 1. Zero-Cost / Free Development Architecture
As required by the specification, the core synchronization platform can be completely developed and tested locally without any paid subscription or real third-party credentials:
- **Database / Broker / Cache**: PostgreSQL, RabbitMQ, and Redis run in local Docker containers.
- **Suppliers & Marketplaces**: Isolated mock adapters (`MockSupplierAdapter` and `MockMarketplaceAdapter`) simulate real API latency, inventory shifts, price swings, network dropouts, and error conditions.

## 2. API Key Inventory & Free Acquisition Guide

| Platform | Role | Sandbox / Free Tier Details |
| :--- | :--- | :--- |
| **eBay Developer Program** | Marketplace listing & inventory sync | **100% Free**. Sign up at [developer.ebay.com](https://developer.ebay.com/). Create a developer keyset (App ID, Dev ID, Cert ID) for the eBay Sandbox environment. |
| **Shopify Partners** | Store listing & inventory management | **100% Free**. Register at [partners.shopify.com](https://partners.shopify.com/). Create unlimited free partner development stores with full Admin API access tokens. |
| **Amazon SP-API** | Amazon marketplace catalog and inventory | Register as an Amazon Developer in Developer Central. The SP-API Sandbox endpoints allow testing orders, catalog, and inventory sync without live selling fees. |
| **Walmart Developer Portal** | Walmart Marketplace API | Sign up at [developer.walmart.com](https://developer.walmart.com). A verified seller account can generate client ID & secret for the sandbox environment. |
| **Newegg Developer Portal** | Newegg Marketplace API | Visit [developer.newegg.com](https://developer.newegg.com). Seller accounts can request sandbox API credentials. |
| **Wholesale Suppliers (Ingram Micro, D&H, TD SYNNEX, Ma Labs, VoiceComm)** | Real-time catalog, stock feeds, pricing | Ingram Micro has a public [Developer Portal](https://developer.ingrammicro.com/) with free sandbox APIs. D&H, TD SYNNEX, Ma Labs, and VoiceComm provide FTP/SFTP/EDI feeds to approved resellers at no software API cost. |
| **Cloudinary** | Cloud image storage & optimization | **Free Tier**: 25 credits/month (~25k transformations or storage) with no credit card required at [cloudinary.com](https://cloudinary.com). Local filesystem is used by default. |
| **Sentry** | Error monitoring & crash reporting | **Free Tier**: Sentry Developer account provides 5,000 events/month for free at [sentry.io](https://sentry.io). |
| **Slack Webhooks** | Alerting for critical sync failures | **100% Free**: Add an Incoming Webhook in any free Slack workspace at [api.slack.com/apps](https://api.slack.com/apps). |

## 3. Credential Encryption at Rest
All supplier and marketplace API secrets stored in the database are encrypted using Fernet (AES-128 in CBC mode with HMAC-SHA256 authenticated encryption) via `CREDENTIAL_ENCRYPTION_KEY`. Secrets are never returned in plain text in API responses or logs.
