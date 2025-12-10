# Numerai - AI-Powered CFO Agent

An intelligent financial transaction processing and management system powered by Claude AI. Built as a multi-tenant SaaS platform for automated transaction classification, invoice processing, revenue recognition, and comprehensive financial dashboards.

## Features

### Core Capabilities

- **AI-Powered Transaction Classification** - Automatic categorization using Claude AI with confidence scoring and pattern learning
- **Smart Document Ingestion** - Intelligent parsing of bank statements, CSV files, and financial documents
- **Invoice Processing** - PDF/OCR processing with automated data extraction using Claude Vision
- **Revenue Recognition** - Match invoices to transactions with AI-assisted reconciliation
- **Multi-Tenant Architecture** - Secure tenant isolation with role-based access control
- **Cryptocurrency Support** - Multi-blockchain transaction tracking with automatic price conversion

### Dashboard Features

- Real-time transaction management with advanced filtering
- Sankey flow charts for cash flow visualization
- Month-end close workflow management
- Business entity management
- Workforce and payroll tracking
- Knowledge base for tenant-specific classification patterns

## Tech Stack

### Backend
- **Python 3.11+** with Flask
- **PostgreSQL** (Cloud SQL compatible)
- **Claude AI** (Anthropic) for intelligent processing
- **Firebase** for authentication
- **Google Cloud Storage** for file storage

### Frontend
- **Next.js 15** with App Router and Turbopack
- **TypeScript**
- **Tailwind CSS** with shadcn/ui components
- **next-intl** for internationalization
- **Recharts** for data visualization

## Project Structure

```
numerai/
├── frontend/                 # Next.js frontend application
│   ├── src/
│   │   ├── app/             # App Router pages
│   │   │   ├── (auth)/      # Authentication pages
│   │   │   └── (dashboard)/ # Protected dashboard pages
│   │   ├── components/      # React components
│   │   │   ├── dashboard/   # Dashboard-specific components
│   │   │   └── ui/          # shadcn/ui components
│   │   ├── context/         # React context providers
│   │   ├── lib/             # Utility functions and API client
│   │   └── messages/        # i18n translation files
│   └── public/              # Static assets
│
├── web_ui/                  # Flask backend application
│   ├── app_db.py           # Main Flask application
│   ├── database.py         # Database connection manager
│   ├── templates/          # Jinja2 templates (legacy UI)
│   ├── static/             # Static assets for legacy UI
│   └── services/           # Business logic services
│
├── api/                     # API route modules
│   ├── auth_routes.py      # Authentication endpoints
│   ├── user_routes.py      # User management
│   └── tenant_routes.py    # Tenant management
│
├── middleware/              # Authentication middleware
├── services/               # Shared services
├── migrations/             # Database migrations
└── main.py                 # Core transaction processing
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Anthropic API key (for Claude AI)
- Firebase project (for authentication)

### Environment Setup

1. Clone the repository:
```bash
git clone https://github.com/Delta-Compute/numerai.git
cd numerai
```

2. Set up Python environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
```

Required environment variables:
```env
# Database
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=numerai
DB_USER=postgres
DB_PASSWORD=your_password

# AI
ANTHROPIC_API_KEY=sk-ant-...

# Firebase (optional, for authentication)
FIREBASE_PROJECT_ID=your-project-id
```

4. Initialize the database:
```bash
psql -h localhost -U postgres -d numerai -f postgres_unified_schema.sql
```

5. Set up the frontend:
```bash
cd frontend
npm install
```

### Running the Application

**Backend (Flask API):**
```bash
cd web_ui
python app_db.py
# Runs on http://localhost:5001
```

**Frontend (Next.js):**
```bash
cd frontend
npm run dev
# Runs on http://localhost:3000
```

### Running in Production

**Backend:**
```bash
gunicorn -w 4 -b 0.0.0.0:5001 web_ui.app_db:app
```

**Frontend:**
```bash
cd frontend
npm run build
npm start
```

## API Documentation

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/transactions` | GET | List transactions |
| `/api/transactions` | POST | Create transaction |
| `/api/invoices` | GET | List invoices |
| `/api/files` | GET | List uploaded files |
| `/api/files/upload` | POST | Upload file for processing |
| `/api/stats` | GET | Dashboard statistics |

### Authentication

All API requests require either:
- `X-Tenant-ID` header for tenant context
- Firebase ID token in `Authorization: Bearer <token>` header

## Development

### Running Tests

```bash
# Backend tests
python -m pytest tests/

# Frontend tests
cd frontend && npm test
```

### Code Style

- Python: Follow PEP 8 guidelines
- TypeScript: ESLint with Prettier

### Database Migrations

Apply migrations in order:
```bash
cd migrations
psql -h localhost -U postgres -d numerai -f <migration_name>.sql
```

## Deployment

### Google Cloud Run

The project includes configuration for Google Cloud Run deployment:

```bash
# Build and deploy
gcloud builds submit --config cloudbuild.yaml
```

### Docker

```bash
docker build -t numerai .
docker run -p 5001:5001 numerai
```

## Architecture

### Multi-Tenant Design

- Complete tenant isolation with `tenant_id` on all data tables
- No fallback tenant logic - explicit tenant context required
- Role-based access control (Fractional CFO, Tenant Admin, Employee)

### AI Integration

- Claude AI for transaction classification with confidence scoring
- Pattern learning from user corrections
- Claude Vision for PDF/document processing

### Security

- Firebase Authentication
- PostgreSQL row-level security
- API key management via Secret Manager
- CORS configuration for frontend

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Proprietary - All rights reserved by Delta Compute.

## Support

For support, please contact the Delta team or open an issue on GitHub.
