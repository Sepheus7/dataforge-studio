# User Authentication Implementation Plan

## Current State

**Simple API Key Authentication:**

- Single API key (`X-API-Key` header)
- No user management
- No granular permissions
- Not suitable for multi-user production

```python
# Current: backend/app/core/auth.py
async def verify_api_key(api_key: str) -> str:
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=403)
    return api_key
```

## Target Architecture

### Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        User Flow                            │
└─────────────────────────────────────────────────────────────┘

1. User Registration
   → Email + Password → Hash password → Store in DB → Send verification email

2. User Login
   → Email + Password → Verify → Generate JWT access + refresh tokens → Return to client

3. Authenticated Request
   → Include JWT in Authorization header → Verify token → Extract user → Allow request

4. Token Refresh
   → Send refresh token → Validate → Generate new access token → Return to client

5. Logout
   → Invalidate refresh token → Clear client storage
```

## Technology Stack

### Backend

- **JWT Tokens**: `python-jose` for encoding/decoding
- **Password Hashing**: `passlib` with bcrypt
- **Database**: SQLAlchemy ORM with SQLite (dev) / PostgreSQL (prod)
- **Validation**: Pydantic models
- **Email**: `fastapi-mail` (optional, for verification)

### Frontend

- **Token Storage**: `httpOnly` cookies or localStorage (with XSS protection)
- **State Management**: Zustand store for auth state
- **HTTP Client**: Axios interceptors for automatic token inclusion
- **Protected Routes**: Higher-order components

## Database Schema

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Refresh tokens table (for token rotation)
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked BOOLEAN DEFAULT FALSE
);

-- Jobs table update (add user ownership)
ALTER TABLE jobs ADD COLUMN user_id UUID REFERENCES users(id);
ALTER TABLE jobs ADD COLUMN shared BOOLEAN DEFAULT FALSE;

-- API Keys table (optional - for programmatic access)
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    prefix VARCHAR(20) NOT NULL,
    last_used TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Implementation Phases

### Phase 1: Backend Foundation (Core Auth)

**Priority: High** | **Estimated: 2-3 days**

#### 1.1 Database Setup

- [ ] Install dependencies: `sqlalchemy`, `alembic`, `psycopg2-binary`
- [ ] Create database models (`models/user.py`)
- [ ] Set up Alembic migrations
- [ ] Create initial migration for users table

```python
# backend/app/models/user.py
from sqlalchemy import Column, String, Boolean, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    role = Column(String(50), default="user")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
```

#### 1.2 Authentication Service

- [ ] Create `services/auth_service.py` with:
  - Password hashing (bcrypt)
  - JWT token generation
  - Token verification
  - User CRUD operations

```python
# backend/app/services/auth_service.py
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)
    
    def verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)
    
    def create_access_token(self, data: dict, expires_delta: timedelta = None):
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")
    
    def create_refresh_token(self, data: dict):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=7)
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, settings.JWT_REFRESH_SECRET, algorithm="HS256")
```

#### 1.3 Auth Dependencies & Middleware

- [ ] Create new `core/auth_jwt.py` (replace old auth.py)
- [ ] Implement `get_current_user` dependency
- [ ] Implement `get_current_active_user` dependency
- [ ] Implement role-based dependencies (`require_admin`, etc.)

```python
# backend/app/core/auth_jwt.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
```

### Phase 2: Auth API Endpoints

**Priority: High** | **Estimated: 2 days**

#### 2.1 Create Auth Routes

- [ ] Create `api/routes_auth.py` with endpoints:
  - `POST /auth/register` - User registration
  - `POST /auth/login` - User login (returns JWT)
  - `POST /auth/refresh` - Refresh access token
  - `POST /auth/logout` - Logout (invalidate refresh token)
  - `GET /auth/me` - Get current user profile
  - `PUT /auth/me` - Update user profile
  - `POST /auth/change-password` - Change password

```python
# backend/app/api/routes_auth.py
@router.post("/auth/register", response_model=UserResponse)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    # Check if user exists
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = User(
        email=request.email,
        username=request.username,
        hashed_password=auth_service.hash_password(request.password),
        full_name=request.full_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user

@router.post("/auth/login", response_model=TokenResponse)
async def login(
    form_data: LoginRequest,
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.email, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect credentials")
    
    access_token = auth_service.create_access_token(data={"sub": str(user.id)})
    refresh_token = auth_service.create_refresh_token(data={"sub": str(user.id)})
    
    # Store refresh token
    db_refresh = RefreshToken(user_id=user.id, token=refresh_token)
    db.add(db_refresh)
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
```

#### 2.2 Request/Response Models

- [ ] Create Pydantic models in `models/auth.py`:
  - `RegisterRequest`, `LoginRequest`, `TokenResponse`
  - `UserResponse`, `UpdateUserRequest`
  - `ChangePasswordRequest`

### Phase 3: Migrate Existing Routes

**Priority: High** | **Estimated: 1 day**

#### 3.1 Update All Protected Routes

- [ ] Replace `verify_api_key` with `get_current_active_user`
- [ ] Update routes to accept `current_user: User` parameter
- [ ] Link jobs to users

```python
# Before
@router.post("/generation/prompt")
async def generate_from_prompt(
    request: PromptRequest,
    api_key: str = Depends(verify_api_key)
):
    ...

# After
@router.post("/generation/prompt")
async def generate_from_prompt(
    request: PromptRequest,
    current_user: User = Depends(get_current_active_user)
):
    job_id = job_manager.create_job(user_id=current_user.id)
    ...
```

#### 3.2 Add User Context to Jobs

- [ ] Update job creation to include user_id
- [ ] Filter job lists by user_id
- [ ] Add permission checks (users can only see their own jobs)

### Phase 4: Frontend Authentication

**Priority: High** | **Estimated: 3 days**

#### 4.1 Auth UI Components

- [ ] Create `frontend/src/components/auth/LoginForm.tsx`
- [ ] Create `frontend/src/components/auth/RegisterForm.tsx`
- [ ] Create `frontend/src/components/auth/AuthLayout.tsx`
- [ ] Add login/signup pages

```typescript
// frontend/src/components/auth/LoginForm.tsx
export const LoginForm = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const login = useAuthStore(state => state.login);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await login(email, password);
      router.push('/');
    } catch (error) {
      toast.error('Login failed');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input type="email" value={email} onChange={e => setEmail(e.target.value)} />
      <input type="password" value={password} onChange={e => setPassword(e.target.value)} />
      <button type="submit">Login</button>
    </form>
  );
};
```

#### 4.2 Auth State Management

- [ ] Create `frontend/src/lib/auth-store.ts` (Zustand)
- [ ] Add auth state: `user`, `tokens`, `isAuthenticated`
- [ ] Add auth actions: `login`, `logout`, `refreshToken`, `loadUser`

```typescript
// frontend/src/lib/auth-store.ts
interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshAccessToken: () => Promise<void>;
  loadUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  
  login: async (email, password) => {
    const response = await api.login({ email, password });
    localStorage.setItem('access_token', response.access_token);
    localStorage.setItem('refresh_token', response.refresh_token);
    set({
      accessToken: response.access_token,
      refreshToken: response.refresh_token,
      isAuthenticated: true
    });
    await get().loadUser();
  },
  
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false });
  },
  
  // ... more actions
}));
```

#### 4.3 Update API Client

- [ ] Add token interceptors to Axios
- [ ] Implement automatic token refresh on 401
- [ ] Update all API calls to use Bearer token

```typescript
// frontend/src/services/api.ts
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Try to refresh token
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await api.post('/auth/refresh', { refresh_token: refreshToken });
        localStorage.setItem('access_token', response.data.access_token);
        // Retry original request
        error.config.headers.Authorization = `Bearer ${response.data.access_token}`;
        return api.request(error.config);
      } catch (refreshError) {
        // Refresh failed, logout
        useAuthStore.getState().logout();
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);
```

#### 4.4 Protected Routes

- [ ] Create `ProtectedRoute` component
- [ ] Wrap authenticated pages
- [ ] Redirect to login if not authenticated

```typescript
// frontend/src/components/ProtectedRoute.tsx
export const ProtectedRoute: React.FC<{ children: ReactNode }> = ({ children }) => {
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return <div>Loading...</div>;
  }

  return <>{children}</>;
};
```

### Phase 5: Advanced Features

**Priority: Medium** | **Estimated: 2-3 days**

#### 5.1 Role-Based Access Control (RBAC)

- [ ] Define roles: `user`, `premium`, `admin`
- [ ] Add role checks to endpoints
- [ ] Frontend role-based UI rendering

```python
# Backend
class RoleEnum(str, Enum):
    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"

def require_role(required_role: RoleEnum):
    async def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role != required_role.value and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_role(RoleEnum.ADMIN))
):
    ...
```

#### 5.2 API Keys for Programmatic Access

- [ ] Generate API keys for users
- [ ] Support both JWT and API key auth
- [ ] API key management UI

#### 5.3 Email Verification

- [ ] Send verification email on registration
- [ ] Verify email endpoint
- [ ] Resend verification email

#### 5.4 Password Reset

- [ ] Forgot password endpoint (send reset email)
- [ ] Reset password with token
- [ ] Password strength requirements

### Phase 6: Security Hardening

**Priority: High** | **Estimated: 1 day**

- [ ] Add rate limiting (using `slowapi`)
- [ ] Implement CORS properly
- [ ] Add password complexity requirements
- [ ] Add account lockout after failed attempts
- [ ] Implement refresh token rotation
- [ ] Add security headers
- [ ] Enable HTTPS in production
- [ ] Audit logging for sensitive operations

### Phase 7: Testing & Documentation

**Priority: Medium** | **Estimated: 2 days**

- [ ] Write unit tests for auth service
- [ ] Write integration tests for auth endpoints
- [ ] Test token refresh flow
- [ ] Test protected routes
- [ ] Update API documentation
- [ ] Create user guide for authentication
- [ ] Document environment variables

## Environment Variables

```bash
# Backend .env
# JWT Configuration
JWT_SECRET=your-super-secret-jwt-key-change-in-production
JWT_REFRESH_SECRET=your-refresh-secret-key-change-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dataforge
# or for development:
DATABASE_URL=sqlite:///./dataforge.db

# Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@dataforge.com

# Security
BCRYPT_ROUNDS=12
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=30

# Keep existing API key for backward compatibility (optional)
API_KEY=dev-key  # For legacy support during migration
```

## Migration Strategy

### Backward Compatibility

To avoid breaking existing deployments, we'll support both auth methods temporarily:

```python
# backend/app/core/auth_hybrid.py
async def get_current_user_hybrid(
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    api_key: Optional[str] = Depends(api_key_header)
) -> User:
    # Try JWT first
    if bearer:
        return await get_current_user(bearer)
    
    # Fall back to API key
    if api_key and api_key == settings.API_KEY:
        # Return a "system" user for API key access
        return get_system_user()
    
    raise HTTPException(status_code=401, detail="Not authenticated")
```

### Migration Steps

1. **Phase 1-3**: Deploy backend with both auth methods
2. **Phase 4**: Deploy frontend with JWT auth
3. **Monitor**: Ensure no API key usage in logs
4. **Phase 5**: Deprecate API key auth (add warnings)
5. **Phase 6**: Remove API key auth completely

## Success Metrics

- [ ] Users can register and login
- [ ] JWT tokens are properly validated
- [ ] Token refresh works automatically
- [ ] Users can only access their own jobs
- [ ] Admin users can access admin endpoints
- [ ] Frontend properly handles auth state
- [ ] Logout clears all auth data
- [ ] Password reset flow works
- [ ] No security vulnerabilities in auth flow
- [ ] All tests pass

## Timeline

**Total Estimated Time: 10-14 days**

| Phase | Days | Priority |
|-------|------|----------|
| Phase 1: Backend Foundation | 2-3 | High |
| Phase 2: Auth API Endpoints | 2 | High |
| Phase 3: Migrate Routes | 1 | High |
| Phase 4: Frontend Auth | 3 | High |
| Phase 5: Advanced Features | 2-3 | Medium |
| Phase 6: Security Hardening | 1 | High |
| Phase 7: Testing & Docs | 2 | Medium |

## Next Steps

1. **Review this plan** and adjust based on priorities
2. **Set up database** (SQLite for dev, PostgreSQL for prod)
3. **Install dependencies** (`sqlalchemy`, `alembic`, `python-jose`, `passlib`)
4. **Start with Phase 1** (Backend Foundation)

## Questions to Decide

1. **Database**: SQLite for dev or jump straight to PostgreSQL?
2. **Email**: Implement now or later?
3. **OAuth**: Add social login (Google, GitHub) or just email/password?
4. **Token Storage**: httpOnly cookies or localStorage?
5. **Session Management**: Allow multiple devices or single session?

---

Ready to start implementing? We can begin with Phase 1 (Backend Foundation). Let me know! 🚀
