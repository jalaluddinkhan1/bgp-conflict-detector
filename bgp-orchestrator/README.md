# BGP Orchestrator

[![CI/CD Pipeline](https://github.com/jalaluddinkhan1/bgp-conflict-detector/actions/workflows/ci.yml/badge.svg)](https://github.com/jalaluddinkhan1/bgp-conflict-detector/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

**Enterprise BGP Network Orchestration and Conflict Detection Platform**

BGP Orchestrator is a production-ready platform for automated BGP configuration management, conflict detection, and network validation. Built with FastAPI, PostgreSQL, and modern DevOps practices.

## Features

- **Automated BGP Configuration Management**: Full CRUD API for BGP peerings with comprehensive validation
- **Conflict Detection**: Real-time detection of ASN collisions, routing loops, and session overlaps using rule-based algorithms
- **Enterprise Security**: OAuth2 integration (Azure AD, Google, Okta), JWT authentication, role-based access control (RBAC), and comprehensive audit logging
- **Observability**: Prometheus metrics, structured logging, and Grafana dashboards for monitoring and analysis
- **Vendor Integration**: Support for Nokia SR OS with extensible driver architecture for additional vendor support
- **External Services**: RIPE RIS integration for historical BGP data, Batfish for network validation, and SuzieQ for device polling
- **Production Ready**: Docker containerization, Kubernetes deployment with Helm charts, CI/CD pipelines, and comprehensive automated testing

## Quick Start

### Using Docker Compose

```bash
# Clone the repository
git clone https://github.com/jalaluddinkhan1/bgp-conflict-detector.git
cd bgp-conflict-detector/bgp-orchestrator

# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Check health
curl http://localhost:8000/healthz

# View API docs
open http://localhost:8000/docs
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run migrations
cd backend
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BGP Orchestrator                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   FastAPI    │  │  PostgreSQL  │  │    Redis     │     │
│  │     API      │◄─┤   Database   │  │    Cache     │     │
│  └──────┬───────┘  └──────────────┘  └──────────────┘     │
│         │                                                    │
│  ┌──────▼───────────────────────────────────────────────┐  │
│  │          Conflict Detection Engine                    │  │
│  │  • ASN Collision  • RPKI Validation                   │  │
│  │  • Session Overlap • Routing Loop Detection          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  RIPE RIS    │  │   Batfish    │  │   SuzieQ     │     │
│  │   Client     │  │   Client     │  │   Client     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Nokia SR   │  │   Cisco      │  │   Juniper    │     │
│  │   OS Driver  │  │   Driver     │  │   Driver     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Observability                                        │  │
│  │  • Prometheus Metrics  • Structured Logging          │  │
│  │  • Audit Trail  • Rate Limiting                      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## API Documentation

Interactive API documentation is available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Security

### Authentication & Authorization

- **OAuth2 Providers**: Azure AD, Google, Okta
- **JWT Tokens**: Access and refresh token support
- **RBAC**: Role-based access control (Admin, Operator, Viewer, Guest)
- **Password Hashing**: bcrypt with salt

### Data Protection

- **Encryption**: Fernet encryption for sensitive data (BGP passwords, SNMP communities)
- **Audit Logging**: Append-only audit trail with HMAC signatures for tamper detection
- **Key Management**: Support for Azure Key Vault and AWS KMS integration

### Security Best Practices

- Non-root Docker containers
- Secrets management via environment variables or KMS
- Rate limiting (10 requests/second per user)
- Input validation and sanitization
- SQL injection protection via SQLAlchemy ORM
- CORS configuration

## Testing

```bash
# Run all tests
pytest tests/ --cov=backend --cov-report=term-missing

# Run unit tests only
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run with coverage report
pytest tests/ --cov=backend --cov-report=html
open htmlcov/index.html
```

**Coverage Target**: >90%

## Deployment

### Docker

```bash
# Build image
docker build -f docker/Dockerfile.backend -t bgp-orchestrator:latest .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_URL=redis://... \
  -e SECRET_KEY=... \
  bgp-orchestrator:latest
```

### Kubernetes (Helm)

```bash
# Install chart
helm install bgp-orchestrator ./helm/bgp-orchestrator \
  --namespace bgp-orchestrator \
  --create-namespace \
  --set image.tag=v1.0.0

# Upgrade
helm upgrade bgp-orchestrator ./helm/bgp-orchestrator \
  --namespace bgp-orchestrator \
  --set image.tag=v1.0.1
```

### Environment Variables

See `.env.example` for required environment variables:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - Secret key for cryptographic operations (min 32 chars)
- `JWT_SECRET_KEY` - JWT signing key
- `OAUTH2_PROVIDER` - OAuth2 provider (azure/google/okta)
- `OAUTH2_CLIENT_ID` - OAuth2 client ID
- `OAUTH2_CLIENT_SECRET` - OAuth2 client secret

## Monitoring

### Prometheus Metrics

Metrics are available at `http://localhost:8000/metrics`:

- `bgp_peerings_total` - Total BGP peerings created
- `conflicts_detected` - Conflicts detected by type
- `api_requests_total` - API request count
- `api_latency_seconds` - API request latency
- `vendor_api_calls_total` - Vendor API calls
- `ripe_ris_latency_seconds` - RIPE RIS latency
- `batfish_validation_duration_seconds` - Batfish validation time

### Grafana Dashboards

Pre-configured dashboards available in `grafana/dashboards/`:
- BGP Orchestrator Overview
- API Performance
- Conflict Detection Metrics
- Vendor Integration Health

## Contributing

We welcome contributions. Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -r backend/requirements.txt
pip install pytest pytest-asyncio pytest-cov fakeredis ruff mypy

# Run linters
ruff check backend/
mypy backend/

# Run tests
pytest tests/ --cov=backend
```

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

## Support

- **Documentation**: See [docs/](docs/) directory
- **Issues**: [GitHub Issues](https://github.com/jalaluddinkhan1/bgp-conflict-detector/issues)

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL toolkit
- [Prometheus](https://prometheus.io/) - Monitoring and alerting
- [Docker](https://www.docker.com/) - Containerization platform
- [Kubernetes](https://kubernetes.io/) - Container orchestration
