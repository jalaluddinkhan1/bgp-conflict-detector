# BGP Conflict Detection System

A production-grade Border Gateway Protocol (BGP) network orchestration and conflict detection system with machine learning-based anomaly detection capabilities.

## Overview

This system provides comprehensive BGP peering session management, automated conflict detection, and predictive analytics for network routing stability. The architecture implements rule-based conflict detection algorithms, machine learning models for BGP flap prediction, and real-time monitoring capabilities.

## Features

- **Conflict Detection**: Rule-based BGP conflict detection implementing algorithms for ASN collision detection, RPKI validation, routing loop detection, and session overlap analysis
- **Machine Learning**: XGBoost-based BGP flap prediction and statistical anomaly detection
- **Observability**: Comprehensive metrics collection, structured logging, and monitoring integration
- **Real-Time Processing**: Kafka integration for streaming BGP update processing
- **Security**: JWT-based authentication, OAuth2 integration, and role-based access control (RBAC)
- **Scalability**: Stateless architecture design supporting horizontal scaling and Kubernetes deployment

## Prerequisites

- Python 3.11 or higher
- PostgreSQL 15 or higher
- Redis 7 or higher
- (Optional) InfluxDB for time-series data storage
- (Optional) Apache Kafka for streaming data processing
- (Optional) VictoriaMetrics for metrics storage

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/jalaluddinkhan1/bgp-conflict-detector.git
cd bgp-conflict-detector/bgp-orchestrator/backend
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configuration

```bash
cp .env.example .env
# Edit .env with your configuration parameters
```

### 4. Database Migration

```bash
alembic upgrade head
```

### 5. Start Application

```bash
python -m app.main
```

The API service will be available at `http://localhost:8000`

## Project Structure

```
backend/
├── app/                    # FastAPI application framework
│   ├── api/               # REST API route definitions
│   ├── config.py          # Application configuration management
│   ├── dependencies.py    # Dependency injection setup
│   └── main.py            # Application entry point
├── core/                   # Core conflict detection algorithms
│   └── conflict_detector.py
├── ml/                     # Machine learning models
│   ├── bgp_flap_predictor.py
│   └── feature_store/
├── models/                 # Database models (SQLAlchemy ORM)
├── schemas/                # Pydantic validation schemas
├── services/               # External service integration clients
├── storage/                # Storage backend implementations (Redis, InfluxDB)
├── utils/                  # Utility modules and helper functions
├── tests/                  # Test suite
├── docs/                   # Documentation
└── deployments/            # Deployment configurations
    ├── k8s/
    └── terraform/
```

## API Documentation

Interactive API documentation is available when the service is running:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

For detailed API reference documentation, see [docs/api.md](docs/api.md).

## Development

### Development Environment Setup

```bash
# Install development dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Execute test suite
pytest tests/

# Run code formatting
black .

# Run static analysis
ruff check .
mypy .
```

### Test Execution

```bash
# Execute all tests
pytest

# Execute with coverage reporting
pytest --cov=. --cov-report=html

# Execute specific test module
pytest tests/unit/test_detector.py
```

## Configuration

See `.env.example` for all available configuration options.

### Key Configuration Variables

- `DATABASE_URL`: PostgreSQL database connection string
- `REDIS_URL`: Redis connection string for caching
- `SECRET_KEY`: Cryptographic secret key (minimum 32 characters)
- `KAFKA_ENABLED`: Enable Kafka streaming integration (default: false)
- `VICTORIAMETRICS_ENABLED`: Enable VictoriaMetrics integration (default: false)
- `FEATURE_STORE_ENABLED`: Enable Feast feature store integration (default: false)

## Deployment

### Docker Deployment

```bash
docker build -t bgp-detector:latest -f Dockerfile .
docker run -p 8000:8000 --env-file .env bgp-detector:latest
```

### Kubernetes Deployment

```bash
kubectl apply -f deployments/k8s/
```

For detailed deployment instructions, see [docs/deployment.md](docs/deployment.md).

## Monitoring

### Metrics

Prometheus metrics are exposed at `/metrics` endpoint:

- HTTP request metrics (count, latency, error rates)
- Machine learning prediction latency
- Anomaly detection metrics
- Conflict detection metrics

### Health Checks

- **Liveness Probe**: `GET /healthz`
- **Readiness Probe**: `GET /readyz`
- **Deep Health Check**: `GET /health/healthz`

## Architecture

For detailed system architecture documentation, see [docs/architecture.md](docs/architecture.md).

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/feature-name`)
3. Implement changes with appropriate tests
4. Execute test suite and linting
5. Submit a pull request

## License

MIT License

## Support

For issues and questions:

- **GitHub Issues**: [Create an issue](https://github.com/jalaluddinkhan1/bgp-conflict-detector/issues)
- **Documentation**: [docs/](docs/)
