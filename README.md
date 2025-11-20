# Nautobot-Style BGP Management Platform

A production-ready, feature-complete web application for managing BGP (Border Gateway Protocol) network infrastructure with a modern, intuitive UI inspired by Nautobot.

## 🚀 Features

- **Complete BGP Management**: Peerings, Peer Groups, Peer Endpoints, Autonomous Systems
- **Advanced Features**: Address Families (AFI-SAFI), Routing Policies, Session State Tracking
- **Modern UI**: React + TypeScript + Tailwind CSS with responsive design
- **Comprehensive API**: RESTful FastAPI backend with validation
- **Bulk Operations**: Multi-select, bulk edit, bulk delete
- **Export**: CSV and JSON export functionality
- **Search & Filter**: Advanced filtering by role, status, state, device, tags
- **Relationship Views**: Topology visualization and peer discovery
- **Audit Trail**: Complete change log with field-level tracking
- **Tags System**: Flexible categorization with color coding

## 📋 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- npm

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -c "from database import init_db; init_db()"
python seed_data.py
python run.py
```

Backend runs on: `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on: `http://localhost:3000`

### Automated Start (Windows)

```powershell
.\start_ui.ps1
```

### Automated Start (Linux/Mac)

```bash
chmod +x start_ui.sh
./start_ui.sh
```

## 🏗️ Architecture

### Backend
- **Framework**: FastAPI (Python)
- **ORM**: SQLAlchemy
- **Database**: SQLite (easily upgradeable to PostgreSQL)
- **Validation**: Pydantic schemas with custom validators

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: TanStack Query (React Query)
- **HTTP Client**: Axios

## 📊 Data Models

- **BGPPeering**: BGP peerings with A-side and Z-side endpoints
- **PeerEndpoint**: Individual peer endpoints with configuration
- **PeerGroup**: Peer groups with templates and policies
- **AutonomousSystem**: AS management with RIR support
- **RoutingInstance**: Per-device BGP instances
- **AddressFamily**: AFI-SAFI support (IPv4, IPv6, VPNv4, L2VPN-EVPN)
- **RoutingPolicy**: Structured routing policies with rules
- **BGPSessionState**: Real-time session state tracking
- **Tag**: Flexible tagging system
- **Secret**: Authentication/encryption management
- **ChangeLog**: Complete audit trail

## 🔧 API Endpoints

### BGP Peerings
- `GET /api/bgp-peerings` - List with filters and pagination
- `GET /api/bgp-peerings/{id}` - Get details
- `POST /api/bgp-peerings` - Create new peering
- `DELETE /api/bgp-peerings/{id}` - Delete peering
- `POST /api/bgp-peerings/bulk-delete` - Bulk delete
- `PUT /api/bgp-peerings/bulk-update` - Bulk update
- `GET /api/bgp-peerings/export/csv` - Export CSV
- `GET /api/bgp-peerings/export/json` - Export JSON
- `GET /api/bgp-peerings/topology` - Get topology graph

### Other Entities
- Address Families, Routing Policies, Tags, Secrets, Session States
- Peer Groups, Peer Endpoints, Autonomous Systems, Devices

See `/docs` for complete API documentation when backend is running.

## ✅ Validation Rules

- ASN: 1-4294967295
- IP Address: IPv4/IPv6 format validation
- Peering Name: Uniqueness check
- Endpoint Relationship: A and Z must be different
- BGP State: Valid state transitions
- AFI-SAFI: Valid combinations
- Hold Time: 0 or 3-65535
- Keepalive: Must be less than hold time

## 🎨 UI Features

- Dashboard with statistics and change log
- BGP Peerings list with advanced filtering
- Detail views for all entities
- Session state monitoring with real-time stats
- Tag management with color coding
- Bulk operations interface
- Export functionality
- Responsive design for mobile and desktop

## 📁 Project Structure

```
.
├── backend/
│   ├── models.py          # SQLAlchemy models
│   ├── schemas.py         # Pydantic schemas
│   ├── main.py            # FastAPI application
│   ├── database.py        # Database configuration
│   ├── validators.py      # Validation rules
│   └── seed_data.py       # Initial data
│
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   ├── lib/           # Utilities and API
│   │   └── App.tsx        # Main app
│   └── package.json
│
└── README.md
```

## 🔒 Security

- Input validation on all endpoints
- SQL injection protection (SQLAlchemy ORM)
- CORS configuration
- Secret encryption ready (implement in production)

## 🚧 Future Enhancements

- Real-time updates with WebSockets
- Graph/Topology visualization UI
- Advanced policy rule builder
- Health monitoring dashboard
- Alerting system
- Authentication and authorization
- Role-based access control

## 📝 License

Open source - use as needed.

## 🤝 Contributing

This is a production-ready reference implementation. Feel free to extend and customize for your needs.
