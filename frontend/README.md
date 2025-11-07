# DataForge Studio - Frontend

Modern React/Next.js frontend for DataForge Studio, an AI-powered synthetic data generation platform.

## Features

- 🤖 **AI Chat Interface** - Natural language data generation using conversational AI
- 📊 **Schema Editor** - Visual database schema designer
- 📈 **Real-time Monitoring** - Live job progress tracking with Server-Sent Events (SSE)
- 💾 **Data Management** - Download generated datasets in CSV/JSON formats
- 🎨 **Modern UI** - Beautiful, responsive design with Tailwind CSS
- 🔄 **Job Dashboard** - Track all your data generation jobs

## Tech Stack

- **Framework**: Next.js 14 with React 18
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **HTTP Client**: Axios
- **Markdown**: React Markdown with syntax highlighting
- **Icons**: Lucide React

## Prerequisites

- Node.js 18+ or Bun
- Backend API running (see `../backend/README.md`)

## Quick Start

### 1. Install Dependencies

```bash
# Using npm
npm install

# Using yarn
yarn install

# Using bun (recommended for speed)
bun install
```

### 2. Configure Environment

Create a `.env.local` file:

```bash
# Backend API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=dev-key
```

### 3. Run Development Server

```bash
# Using npm
npm run dev

# Using yarn
yarn dev

# Using bun
bun dev
```

The app will be available at [http://localhost:3000](http://localhost:3000)

## Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── views/          # Page views
│   │   │   ├── ChatView.tsx      # AI chat interface
│   │   │   ├── SchemaView.tsx    # Schema editor
│   │   │   ├── JobsView.tsx      # Job monitoring
│   │   │   └── SettingsView.tsx  # Settings
│   │   ├── Layout.tsx      # Main layout with sidebar
│   │   └── JobStreamMonitor.tsx  # SSE job monitoring
│   ├── services/           # API services
│   │   └── api.ts         # Backend API client
│   ├── lib/               # Utilities
│   │   ├── store.ts       # Zustand state management
│   │   └── utils.ts       # Helper functions
│   ├── pages/             # Next.js pages
│   │   ├── _app.tsx       # App wrapper
│   │   ├── _document.tsx  # HTML document
│   │   └── index.tsx      # Main page
│   └── styles/
│       └── globals.css    # Global styles
├── public/                # Static assets
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── next.config.js
```

## Usage

### Chat Interface

1. Navigate to the **Chat** tab
2. Type your data generation request in natural language
3. The AI will create a schema and generate synthetic data
4. Monitor progress in the **Jobs** tab

**Example prompts:**
- "Generate a customer database with orders and products"
- "Create synthetic user data with 1000 records"
- "Generate an e-commerce dataset with transactions"

### Schema Editor

1. Go to the **Schema Editor** tab
2. Design your database schema visually:
   - Add/remove tables
   - Define columns with types
   - Set row counts
3. Click **Generate Data** to create synthetic data
4. Download results from the **Jobs** tab

### Jobs Dashboard

- View all generation jobs
- Monitor real-time progress with SSE
- Download completed datasets
- Retry failed jobs
- Delete old jobs

### Settings

- Test backend connection
- View backend health status
- Configure API URL and key
- Check version information

## API Integration

The frontend communicates with the DataForge backend API:

### Endpoints Used

- `POST /v1/generation/prompt` - Generate from natural language
- `POST /v1/generation/schema` - Generate from schema
- `GET /v1/generation/{job_id}` - Get job status
- `GET /v1/generation/{job_id}/stream` - SSE job updates
- `GET /v1/generation/{job_id}/download` - Download artifacts
- `DELETE /v1/generation/{job_id}` - Cancel job
- `GET /healthz` - Health check

### Authentication

All requests include the `X-API-Key` header for authentication.

## Development

### Available Scripts

```bash
# Development server
npm run dev

# Production build
npm run build

# Start production server
npm start

# Lint code
npm run lint

# Type check
npm run type-check
```

### Code Style

- TypeScript for type safety
- Functional React components with hooks
- Tailwind CSS for styling
- ESLint for code quality

## Building for Production

```bash
# Build the application
npm run build

# Start production server
npm start
```

The build output will be in the `.next/` directory.

## Deployment

### Option 1: Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

### Option 2: Docker

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

### Option 3: Static Export

For static hosting (Netlify, S3, etc.):

```js
// next.config.js
module.exports = {
  output: 'export',
  // ... other config
}
```

Then run:

```bash
npm run build
# Output will be in the 'out' directory
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000` |
| `NEXT_PUBLIC_API_KEY` | API authentication key | `dev-key` |

## Troubleshooting

### Backend Connection Failed

**Problem**: "No response from server" error

**Solution**:
1. Ensure backend is running: `cd ../backend && make dev`
2. Check API URL in Settings
3. Verify API key matches backend configuration

### SSE Not Working

**Problem**: Real-time updates not appearing

**Solution**:
1. Check browser console for errors
2. Ensure backend streaming endpoint is working
3. Try refreshing the page

### Build Errors

**Problem**: TypeScript or build errors

**Solution**:
```bash
# Clear cache and reinstall
rm -rf .next node_modules
npm install
npm run build
```

## Browser Support

- Chrome/Edge: Latest 2 versions
- Firefox: Latest 2 versions
- Safari: Latest 2 versions
- Mobile: iOS Safari 12+, Chrome Android

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `npm run lint` and `npm run type-check`
5. Submit a pull request

## License

MIT

## Support

- 📚 [Documentation](../docs/)
- 🐛 [Report Issues](https://github.com/yourusername/dataforge-studio/issues)
- 💬 [Discussions](https://github.com/yourusername/dataforge-studio/discussions)

