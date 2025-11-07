# Frontend Setup Guide

Complete guide to setting up and running the DataForge Studio frontend.

## Prerequisites

- **Node.js 18+** or **Bun** (recommended)
- **Backend running** at http://localhost:8000
- Modern web browser

## Quick Start

### 1. Install Dependencies

```bash
cd frontend

# Using npm
npm install

# Using yarn
yarn install

# Using bun (fastest!)
bun install
```

### 2. Configure Environment

The frontend is pre-configured with sensible defaults. For custom configuration, create `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=dev-key
```

### 3. Start Development Server

```bash
# Using Make (recommended)
make dev

# Or using npm
npm run dev

# Or using bun
bun dev
```

The frontend will be available at **http://localhost:3000** 🎉

## Using the Application

### 1. AI Chat Interface

The main feature for natural language data generation:

**Navigate to Chat tab:**
- Type your data request in plain English
- Example: "Generate a customer database with 1000 users"
- The AI will create a schema and generate data
- Monitor progress in Jobs tab

**Example Prompts:**
```
Generate a customer database with orders and products
Create synthetic user data with 1000 records
Generate an e-commerce dataset with transactions
Create a healthcare patient dataset with demographics
Generate financial transaction data for a bank
```

### 2. Schema Editor

For manual schema design:

**Navigate to Schema Editor tab:**
- Add tables and define columns
- Set data types (string, integer, email, phone, etc.)
- Specify row counts
- Click "Generate Data"
- Download results from Jobs tab

**Supported Column Types:**
- `integer` - Whole numbers
- `string` - Text data
- `email` - Email addresses
- `phone` - Phone numbers
- `name` - Person names
- `address` - Street addresses
- `date` - Dates (YYYY-MM-DD)
- `datetime` - Timestamps
- `boolean` - True/False
- `float` - Decimal numbers
- `url` - Web URLs
- `uuid` - UUIDs

### 3. Jobs Dashboard

Monitor all generation jobs:

- **Real-time updates** via Server-Sent Events
- **Progress tracking** with percentage
- **Download results** in CSV/JSON
- **View sample data** inline
- **Retry failed jobs**
- **Delete old jobs**

### 4. Settings

Configure backend connection:

- Test API connection
- View backend health status
- Check version information
- Verify LLM provider setup

## Architecture

### Frontend Stack

```
Next.js 14 (React Framework)
├── TypeScript (Type Safety)
├── Tailwind CSS (Styling)
├── Zustand (State Management)
├── Axios (HTTP Client)
├── React Markdown (Content Rendering)
└── Lucide React (Icons)
```

### Key Features

1. **Server-Side Rendering (SSR)**
   - Fast initial page loads
   - SEO-friendly
   - Better performance

2. **Real-time Updates**
   - SSE for job progress
   - Live status updates
   - No polling needed

3. **Type Safety**
   - TypeScript throughout
   - API types matching backend
   - Compile-time error checking

4. **Responsive Design**
   - Mobile-friendly
   - Tablet optimized
   - Desktop focused

## API Integration

### Backend Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/generation/prompt` | POST | Generate from natural language |
| `/v1/generation/schema` | POST | Generate from schema |
| `/v1/generation/{job_id}` | GET | Get job status |
| `/v1/generation/{job_id}/stream` | GET | Stream job updates (SSE) |
| `/v1/generation/{job_id}/download` | GET | Download artifacts |
| `/v1/generation/{job_id}` | DELETE | Cancel job |
| `/healthz` | GET | Health check |

### Authentication

All requests include the `X-API-Key` header:

```typescript
headers: {
  'X-API-Key': 'dev-key',
  'Content-Type': 'application/json'
}
```

## Development

### Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── views/              # Main views
│   │   │   ├── ChatView.tsx    # AI chat interface
│   │   │   ├── SchemaView.tsx  # Schema editor
│   │   │   ├── JobsView.tsx    # Jobs dashboard
│   │   │   └── SettingsView.tsx
│   │   ├── Layout.tsx          # App layout
│   │   └── JobStreamMonitor.tsx # SSE monitor
│   ├── services/
│   │   └── api.ts              # API client
│   ├── lib/
│   │   ├── store.ts            # State management
│   │   └── utils.ts            # Utilities
│   ├── pages/
│   │   └── index.tsx           # Main page
│   └── styles/
│       └── globals.css
├── public/                     # Static files
└── package.json
```

### Available Commands

```bash
make help        # Show all commands
make install     # Install dependencies
make dev         # Start dev server
make build       # Build for production
make start       # Start production server
make lint        # Run linter
make type-check  # TypeScript check
make clean       # Clean artifacts
```

### Adding New Features

1. **New View**:
   - Create component in `src/components/views/`
   - Add route in `src/pages/index.tsx`
   - Add nav item in `src/components/Layout.tsx`

2. **New API Endpoint**:
   - Add method to `src/services/api.ts`
   - Define TypeScript types
   - Update API client

3. **New State**:
   - Add to Zustand store in `src/lib/store.ts`
   - Create actions and selectors
   - Use in components with `useAppStore()`

## Building for Production

### Local Production Build

```bash
# Build
make build

# Start production server
make start
```

### Docker Build

Create `Dockerfile`:

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
EXPOSE 3000
CMD ["npm", "start"]
```

Build and run:

```bash
docker build -t dataforge-frontend .
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://backend:8000 \
  -e NEXT_PUBLIC_API_KEY=dev-key \
  dataforge-frontend
```

## Deployment

### Option 1: Vercel (Easiest)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Set environment variables in Vercel dashboard
```

### Option 2: AWS (with backend)

Deploy alongside backend on EKS:

1. Build Docker image
2. Push to ECR
3. Update K8s deployment
4. Configure Ingress

See `infrastructure/k8s/README.md` for details.

### Option 3: Static Export

For Netlify, S3, Cloudflare Pages:

```js
// next.config.js
module.exports = {
  output: 'export',
  images: {
    unoptimized: true,
  },
}
```

```bash
npm run build
# Output in 'out/' directory
```

## Troubleshooting

### Backend Connection Issues

**Error**: "No response from server"

**Solution**:
```bash
# 1. Check backend is running
curl http://localhost:8000/healthz

# 2. Check CORS settings in backend
# backend/app/core/config.py
CORS_ORIGINS = ["http://localhost:3000"]

# 3. Verify API key matches
# frontend/.env.local
NEXT_PUBLIC_API_KEY=dev-key

# backend/.env
API_KEY=dev-key
```

### SSE Not Working

**Error**: Real-time updates not appearing

**Solution**:
```bash
# 1. Check browser console for errors
# 2. Verify SSE endpoint in backend
curl http://localhost:8000/v1/generation/{job_id}/stream

# 3. Check EventSource support
# Modern browsers should work, IE not supported
```

### Build Errors

**Error**: TypeScript or build failures

**Solution**:
```bash
# Clear cache
rm -rf .next node_modules
npm install
npm run build

# Check Node version
node --version  # Should be 18+
```

### CORS Errors

**Error**: "Access-Control-Allow-Origin"

**Solution**:
```python
# backend/app/core/config.py
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    # Add your frontend URLs
]
```

## Performance Optimization

### Tips for Production

1. **Enable Static Generation** where possible
2. **Use Image Optimization** with Next.js Image
3. **Implement Code Splitting** (automatic with Next.js)
4. **Add Caching Headers** for static assets
5. **Use CDN** for global distribution
6. **Enable Compression** (gzip/brotli)

### Monitoring

Track performance with:
- Vercel Analytics
- Google Lighthouse
- Web Vitals
- Custom metrics

## Security

### Best Practices

1. **API Keys**: Never commit to Git
2. **Environment Variables**: Use `.env.local`
3. **HTTPS**: Always use in production
4. **Content Security Policy**: Configure in Next.js
5. **Rate Limiting**: Implement in backend
6. **Input Validation**: Always validate user input

## Testing

### Manual Testing Checklist

- [ ] Chat interface sends prompts
- [ ] Schema editor creates valid schemas
- [ ] Jobs dashboard shows jobs
- [ ] SSE updates work in real-time
- [ ] Downloads work for all formats
- [ ] Settings shows backend status
- [ ] Mobile responsive design works
- [ ] Dark mode (if implemented)

### Automated Testing (Future)

```bash
# Unit tests
npm run test

# E2E tests
npm run test:e2e

# Coverage
npm run test:coverage
```

## Support

- 📖 **Documentation**: See `docs/` directory
- 🐛 **Issues**: GitHub Issues
- 💬 **Discussions**: GitHub Discussions
- 📧 **Email**: support@example.com

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit PR

## License

MIT

---

**Ready to go!** 🚀

Start the backend, then the frontend, and visit http://localhost:3000

