# BGP Conflict Detector

Enterprise-grade BGP network orchestration and conflict detection system with ML-based anomaly detection.

## Features

- 🔍 **Conflict Detection**: Rule-based BGP conflict detection (ASN collision, RPKI validation, routing loops)
- 🤖 **ML-Powered**: XGBoost-based BGP flap prediction and anomaly detection
- 📊 **Observability**: Comprehensive metrics, logging, and monitoring
- ⚡ **Real-Time**: Kafka integration for streaming BGP updates
- 🔒 **Secure**: JWT authentication, OAuth2, role-based access control
- 🚀 **Scalable**: Stateless design, horizontal scaling, Kubernetes-ready

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- (Optional) InfluxDB, Kafka, VictoriaMetrics

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd bgp-orchestrator/backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run database migrations:
```bash
alembic upgrade head
```

5. Start the application:
```bash
python -m app.main
```

The API will be available at `http://localhost:8000`

## Project Structure

```
backend/
├── app/                    # FastAPI application
│   ├── api/               # API routes
│   ├── config.py          # Configuration
│   ├── dependencies.py    # Dependency injection
│   └── main.py            # Application entry point
├── core/                   # Core conflict detection
│   └── conflict_detector.py
├── ml/                     # Machine learning models
│   ├── bgp_flap_predictor.py
│   └── feature_store/
├── models/                 # Database models
├── schemas/                # Pydantic schemas
├── services/               # External service clients
├── storage/                # Storage backends (Redis, InfluxDB)
├── utils/                  # Utility modules
├── tests/                  # Test suite
├── docs/                   # Documentation
└── deployments/            # Deployment configs
    ├── k8s/
    └── terraform/
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

See [docs/api.md](docs/api.md) for detailed API reference.

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run linting
black .
ruff check .
mypy .
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/test_detector.py
```

## Configuration

See `.env.example` for all available configuration options.

### Key Configuration Variables

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: Secret key for cryptography (min 32 chars)
- `KAFKA_ENABLED`: Enable Kafka streaming (default: false)
- `VICTORIAMETRICS_ENABLED`: Enable VictoriaMetrics (default: false)
- `FEATURE_STORE_ENABLED`: Enable Feast feature store (default: false)

## Deployment

### Docker

```bash
docker build -t bgp-detector:latest -f Dockerfile .
docker run -p 8000:8000 --env-file .env bgp-detector:latest
```

### Kubernetes

```bash
kubectl apply -f deployments/k8s/
```

See [docs/deployment.md](docs/deployment.md) for detailed deployment guide.

## Monitoring

### Metrics

Prometheus metrics are exposed at `/metrics`:
- HTTP request metrics
- ML prediction latency
- Anomaly detection metrics
- Conflict detection metrics

### Health Checks

- Liveness: `GET /healthz`
- Readiness: `GET /readyz`
- Deep Health: `GET /health/healthz`

## Architecture

See [docs/architecture.md](docs/architecture.md) for system architecture overview.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License

## Support

For issues and questions:
- GitHub Issues: [Create an issue](https://github.com/yourorg/bgp-conflict-detector/issues)
- Documentation: [docs/](docs/)

