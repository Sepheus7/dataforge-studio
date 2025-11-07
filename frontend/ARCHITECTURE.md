# Frontend Architecture

This document explains the architecture and design decisions of the DataForge Studio frontend.

## Overview

```
┌─────────────────────────────────────────────────────────┐
│                     User Browser                        │
│                   http://localhost:3000                 │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ React Components
                  │
┌─────────────────▼───────────────────────────────────────┐
│                    Next.js App                          │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │              Layout Component                   │    │
│  │  ┌──────────┬──────────────────────────────┐  │    │
│  │  │ Sidebar  │    Main Content Area         │  │    │
│  │  │          │                               │  │    │
│  │  │ Chat     │  ┌────────────────────────┐  │  │    │
│  │  │ Schema   │  │   Current View         │  │  │    │
│  │  │ Jobs     │  │                        │  │  │    │
│  │  │ Settings │  │  - ChatView            │  │  │    │
│  │  │          │  │  - SchemaView          │  │  │    │
│  │  │          │  │  - JobsView            │  │  │    │
│  │  │          │  │  - SettingsView        │  │  │    │
│  │  │          │  │                        │  │  │    │
│  │  └──────────┴──┴────────────────────────┘  │  │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │           State Management (Zustand)           │    │
│  │  - Jobs state                                  │    │
│  │  - UI state (sidebar, current view)            │    │
│  │  - Active job tracking                         │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │           API Service Layer                    │    │
│  │  - HTTP client (Axios)                         │    │
│  │  - SSE handling (EventSource)                  │    │
│  │  - Error handling                              │    │
│  │  - Type definitions                            │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ HTTP / SSE
                  │
┌─────────────────▼───────────────────────────────────────┐
│              FastAPI Backend                            │
│            http://localhost:8000                        │
│                                                          │
│  REST API:                                              │
│  - POST /v1/generation/prompt                          │
│  - POST /v1/generation/schema                          │
│  - GET  /v1/generation/{job_id}                        │
│  - GET  /v1/generation/{job_id}/stream (SSE)           │
│  - GET  /v1/generation/{job_id}/download               │
│  - DELETE /v1/generation/{job_id}                      │
│  - GET  /healthz                                        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Component Architecture

### Main Components

```
App (_app.tsx)
│
├── Layout
│   ├── Sidebar Navigation
│   │   ├── Logo
│   │   ├── Navigation Items
│   │   └── Footer
│   │
│   └── Main Content
│       └── Current View (based on routing)
│
├── Views
│   ├── ChatView
│   │   ├── Message List
│   │   ├── Message Input
│   │   └── Example Prompts
│   │
│   ├── SchemaView
│   │   ├── Table Editor
│   │   │   ├── Table Header
│   │   │   ├── Column Editor
│   │   │   └── Add Column Button
│   │   ├── Add Table Button
│   │   └── Generate Button
│   │
│   ├── JobsView
│   │   ├── Job List
│   │   │   ├── Job Card
│   │   │   │   ├── Status Badge
│   │   │   │   ├── Job Details
│   │   │   │   ├── Results Display
│   │   │   │   └── Actions (Download, Delete)
│   │   │   └── JobStreamMonitor (for active jobs)
│   │   └── Refresh Button
│   │
│   └── SettingsView
│       ├── Connection Settings
│       ├── Health Status
│       └── About Section
│
└── Shared Components
    └── JobStreamMonitor
        ├── Progress Bar
        └── Event Log
```

## Data Flow

### 1. Chat Interface Flow

```
User types prompt
       ↓
ChatView component
       ↓
api.generateFromPrompt()
       ↓
POST /v1/generation/prompt
       ↓
Backend creates job
       ↓
Job ID returned
       ↓
Add job to Zustand store
       ↓
Show success message
       ↓
User switches to Jobs tab
       ↓
JobsView shows job
       ↓
JobStreamMonitor connects SSE
       ↓
Real-time updates flow in
       ↓
Job completes
       ↓
Download button enabled
```

### 2. Schema Editor Flow

```
User designs schema
       ↓
Adds tables + columns
       ↓
Clicks "Generate Data"
       ↓
SchemaView validates
       ↓
api.generateFromSchema()
       ↓
POST /v1/generation/schema
       ↓
Backend creates job
       ↓
Job ID returned
       ↓
Add job to store
       ↓
Redirect to Jobs tab
       ↓
Monitor progress with SSE
```

### 3. Real-time Updates Flow

```
JobStreamMonitor mounts
       ↓
Create EventSource
       ↓
GET /v1/generation/{job_id}/stream
       ↓
SSE connection opened
       ↓
Backend sends events:
  - progress updates
  - status changes
  - result data
       ↓
EventSource.onmessage
       ↓
Parse event data
       ↓
Update Zustand store
       ↓
Components re-render
       ↓
User sees live updates
       ↓
Job completes
       ↓
Close SSE connection
```

## State Management

### Zustand Store Structure

```typescript
{
  // Jobs storage
  jobs: {
    [jobId: string]: {
      job_id: string,
      status: JobStatus,
      created_at: string,
      started_at?: string,
      completed_at?: string,
      result?: any,
      error?: string,
      progress?: number
    }
  },
  
  // UI state
  activeJobId: string | null,
  sidebarOpen: boolean,
  currentView: 'chat' | 'schema' | 'jobs' | 'settings',
  
  // Actions
  addJob: (job) => void,
  updateJob: (jobId, updates) => void,
  removeJob: (jobId) => void,
  setActiveJob: (jobId) => void,
  setSidebarOpen: (open) => void,
  setCurrentView: (view) => void
}
```

### State Updates

```
User Action → Component → Zustand Action → State Update → Re-render
```

Example:
```
Click "Generate" → ChatView → addJob() → jobs[id] = {...} → JobsView re-renders
```

## API Layer

### API Client Structure

```typescript
class DataForgeAPI {
  private client: AxiosInstance;
  
  // Generation endpoints
  generateFromPrompt(request): Promise<JobResponse>
  generateFromSchema(request): Promise<JobResponse>
  getJobStatus(jobId): Promise<JobStatusResponse>
  cancelJob(jobId): Promise<{...}>
  getDownloadUrl(jobId, table, format): string
  
  // Streaming
  createJobStream(jobId): EventSource
  
  // Documents
  generateDocument(request): Promise<DocumentResponse>
  
  // Health
  healthCheck(): Promise<any>
}
```

### Error Handling

```
API Call
   ↓
Axios Request
   ↓
Response Interceptor
   ↓
Success? ──Yes→ Return data
   ↓
   No
   ↓
Create APIError
   ↓
Throw with details
   ↓
Catch in component
   ↓
Show error message
```

## Routing

### Next.js Page Router

```
/                       → index.tsx (main page)
  ├─ view=chat         → ChatView
  ├─ view=schema       → SchemaView
  ├─ view=jobs         → JobsView
  └─ view=settings     → SettingsView
```

Routing is handled by Zustand state (`currentView`), not URL routing.

## Styling

### Tailwind CSS Architecture

```
Global Styles (globals.css)
   ↓
Tailwind Base
   ↓
Component Styles (inline classes)
   ↓
Utility Classes
   ↓
Custom Utilities (tailwind.config.js)
```

### Theme Structure

```javascript
// tailwind.config.js
{
  colors: {
    primary: { 50-900 },  // Brand colors
    ...default colors
  },
  spacing: { ... },        // Standard spacing
  breakpoints: {
    sm: '640px',          // Mobile
    md: '768px',          // Tablet
    lg: '1024px',         // Desktop
    xl: '1280px'          // Large desktop
  }
}
```

## Performance Optimizations

### 1. Code Splitting

```
Next.js automatically splits:
- Each page
- Each component
- Third-party libraries
```

### 2. SSR (Server-Side Rendering)

```
Initial request → Server renders → Send HTML → Hydrate → Interactive
```

Benefits:
- Fast first paint
- SEO friendly
- Better performance

### 3. Optimized Images

```
<Image /> component:
- Automatic optimization
- Lazy loading
- WebP conversion
- Responsive images
```

### 4. State Updates

```
Zustand selector → Only re-render affected components
```

Example:
```typescript
// Only re-renders when jobs change, not for UI state
const jobs = useAppStore(state => state.jobs);
```

## Security

### 1. API Authentication

```
Request → Add X-API-Key header → Backend validates → Allow/Deny
```

### 2. Environment Variables

```
Build time:
.env.local → process.env.NEXT_PUBLIC_* → Embedded in bundle

Runtime (server):
.env → process.env.* → Server only
```

### 3. XSS Protection

```
User input → React escapes → Safe render
```

React automatically escapes all output.

### 4. CORS

```
Frontend (localhost:3000) → Backend checks CORS → Allow if whitelisted
```

## Deployment Architecture

### Development

```
npm run dev → Next.js Dev Server → Hot reload → Browser
```

### Production

```
npm run build → Optimize & Bundle → Static files + Server
       ↓
npm start → Next.js Server → Serve app
```

### Docker

```
Dockerfile → Build → Image → Container → Running app
```

### Vercel

```
Push to Git → Vercel detects → Build → Deploy → CDN
```

## File Organization

```
frontend/
├── src/                    # Source code
│   ├── components/         # React components
│   │   ├── views/         # Page views
│   │   └── *.tsx          # Shared components
│   ├── services/          # External services
│   │   └── api.ts         # API client
│   ├── lib/               # Utilities
│   │   ├── store.ts       # State management
│   │   └── utils.ts       # Helpers
│   ├── pages/             # Next.js pages
│   └── styles/            # Global styles
├── public/                # Static assets
├── package.json           # Dependencies
├── tsconfig.json          # TypeScript config
├── tailwind.config.js     # Tailwind config
└── next.config.js         # Next.js config
```

## Development Workflow

```
1. Create feature branch
2. Make changes
3. Test locally (npm run dev)
4. Type check (npm run type-check)
5. Lint (npm run lint)
6. Build (npm run build)
7. Commit & push
8. Deploy
```

## Testing Strategy

### Manual Testing

- Browser testing (Chrome, Firefox, Safari)
- Responsive testing (mobile, tablet, desktop)
- API integration testing
- SSE functionality testing

### Automated Testing (Future)

```
Unit Tests → Jest/Vitest
Component Tests → React Testing Library
E2E Tests → Playwright/Cypress
```

## Monitoring

### Development

- Browser DevTools
- React DevTools
- Network tab for API calls
- Console for errors

### Production (Future)

- Vercel Analytics
- Error tracking (Sentry)
- Performance monitoring
- User analytics

---

## Key Design Decisions

1. **Next.js** - For SSR, routing, and optimizations
2. **TypeScript** - For type safety and better DX
3. **Zustand** - Lightweight, simple state management
4. **Tailwind** - Rapid development, consistent design
5. **Axios** - Better error handling than fetch
6. **SSE** - Real-time updates without polling
7. **Component-based** - Reusable, maintainable code
8. **API Service Layer** - Centralized API logic

## Future Enhancements

- [ ] Dark mode support
- [ ] User authentication
- [ ] Job history persistence
- [ ] Data preview in modal
- [ ] Export to multiple formats
- [ ] Schema templates
- [ ] Advanced filtering
- [ ] Keyboard shortcuts
- [ ] Accessibility improvements
- [ ] Performance monitoring
- [ ] Automated testing
- [ ] i18n support

