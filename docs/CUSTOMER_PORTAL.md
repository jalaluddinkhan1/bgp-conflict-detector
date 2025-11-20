# Customer Portal Documentation

## Overview

The Customer Portal provides a self-service dashboard for customers to manage their BGP Orchestrator account, view usage statistics, manage billing, and configure preferences.

## Features

### 1. Usage Statistics
- BGP peerings count (with limit tracking)
- API requests this month
- Data transfer usage
- ML predictions count
- Storage usage

### 2. Invoice Management
- View all invoices
- Download invoices
- Track payment status
- View invoice history

### 3. Support Tickets
- Create support tickets
- Track ticket status
- View ticket history
- Priority management

### 4. Billing Plan Management
- View current plan
- Compare available plans
- Change plan
- View plan features and limits

### 5. API Key Management
- Create API keys
- View API keys
- Delete API keys
- Track API key usage

### 6. Alert Preferences
- Configure email alerts
- Configure Slack alerts
- Set webhook URLs
- Configure alert severity levels

## Authentication

The Customer Portal uses **Keycloak SSO** for authentication.

### Setup

1. **Configure Keycloak**:
   - Create realm: `bgp-orchestrator`
   - Create client: `bgp-orchestrator-frontend`
   - Configure redirect URIs

2. **Environment Variables**:
   ```bash
   VITE_KEYCLOAK_URL=http://localhost:8080
   VITE_KEYCLOAK_REALM=bgp-orchestrator
   VITE_KEYCLOAK_CLIENT_ID=bgp-orchestrator-frontend
   ```

3. **Backend Integration**:
   - Backend validates Keycloak tokens
   - User information extracted from token
   - Role-based access control

## API Endpoints

All customer portal endpoints are under `/api/v1/customer/`:

- `GET /api/v1/customer/usage-stats` - Get usage statistics
- `GET /api/v1/customer/invoices` - Get invoices
- `GET /api/v1/customer/support-tickets` - Get support tickets
- `GET /api/v1/customer/plan` - Get current plan
- `GET /api/v1/customer/plans` - Get available plans
- `POST /api/v1/customer/change-plan` - Change billing plan
- `GET /api/v1/customer/api-keys` - Get API keys
- `POST /api/v1/customer/api-keys` - Create API key
- `DELETE /api/v1/customer/api-keys/{key_id}` - Delete API key
- `GET /api/v1/customer/alert-preferences` - Get alert preferences
- `PUT /api/v1/customer/alert-preferences` - Update alert preferences

## Usage

### Accessing the Portal

1. Navigate to `/customer-portal`
2. If not authenticated, you'll be redirected to Keycloak login
3. After login, you'll be redirected back to the portal

### Viewing Usage

The dashboard shows real-time usage statistics:
- Current usage vs. plan limits
- Monthly API request count
- Data transfer usage
- ML prediction usage

### Managing API Keys

1. Click "Create New API Key"
2. Enter a name for the key
3. Copy the generated key (shown only once)
4. Use the key in API requests: `Authorization: Bearer <key>`

### Changing Plans

1. View available plans
2. Click "Change Plan" on desired plan
3. Confirm the change
4. Plan change takes effect immediately (or on next billing cycle)

### Configuring Alerts

1. Toggle email/Slack alerts
2. Enter webhook URL (if using webhooks)
3. Select alert severity levels
4. Changes save automatically

## Security

- All endpoints require authentication
- Keycloak tokens validated on backend
- API keys are hashed and stored securely
- Rate limiting on all endpoints
- Audit logging for all actions

## Related Documentation

- [Keycloak Setup](../docs/KEYCLOAK_SETUP.md)
- [API Documentation](../docs/API.md)
- [Authentication Guide](../docs/AUTHENTICATION.md)

