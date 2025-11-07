# 🚀 Quick Start Guide

Get DataForge Studio running in 2 minutes!

## Prerequisites Check

```bash
# Check conda
conda --version

# Check Node.js
node --version

# Both should return version numbers
```

## One-Command Start (Easiest!)

Open a terminal and run:

```bash
cd /Users/romainboluda/Documents/PersonalProjects/dataforge-studio

# Activate the conda environment first
conda activate dataforge-studio

# Start everything with one command
./scripts/start.sh
```

This single script will:

- ✅ Check all prerequisites
- ✅ Start backend on <http://localhost:8000>
- ✅ Start frontend on <http://localhost:3000>
- ✅ Show you live logs from both
- ✅ Handle cleanup when you press Ctrl+C

You should see:

```
✅ All services are running!

🌐 URLs:
   Frontend:  http://localhost:3000
   Backend:   http://localhost:8000
   API Docs:  http://localhost:8000/v1/docs

🛑 To stop: Press Ctrl+C
```

**That's it!** Open <http://localhost:3000> in your browser 🎉

## Alternative: Separate Scripts

If you prefer to run backend and frontend separately:

### Terminal 1 - Backend

```bash
./scripts/start-backend.sh
```

### Terminal 2 - Frontend

```bash
./scripts/start-frontend.sh
```

## Verify Backend Connection

1. Click **Settings** in the sidebar
2. Click **Test Connection**
3. You should see a green "Connected" status

## Common Issues

### Backend Won't Start

**Error**: "conda environment not found"

**Fix**:

```bash
conda env list | grep dataforge-studio

# If not found, create it:
make setup
```

**Error**: "Port 8000 already in use"

**Fix**:

```bash
# Kill old processes
pkill -f "uvicorn.*8000"

# Then restart
./scripts/start-backend.sh
```

### Frontend Won't Start

**Error**: "node_modules not found"

**Fix**:

```bash
cd frontend
npm install
cd ..
./start-frontend.sh
```

**Error**: "Port 3000 already in use"

**Fix**:

```bash
# Kill old processes
lsof -ti:3000 | xargs kill -9

# Then restart
./scripts/start-frontend.sh
```

### Backend Shows "Not Found"

**Solution**: Make sure backend is running first!

```bash
# Check if backend is running
curl http://localhost:8000/healthz

# Should return:
{"status":"healthy",...}
```

## Manual Start (Alternative)

If the scripts don't work, start manually:

### Backend

```bash
cd /Users/romainboluda/Documents/PersonalProjects/dataforge-studio
conda activate dataforge-studio
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd /Users/romainboluda/Documents/PersonalProjects/dataforge-studio/frontend
npm run dev
```

## Stop Services

### To stop backend

Press `Ctrl+C` in Terminal 1

### To stop frontend

Press `Ctrl+C` in Terminal 2

## Quick Commands Reference

```bash
# Start both services
./scripts/start-backend.sh    # Terminal 1
./scripts/start-frontend.sh   # Terminal 2

# Check if running
curl http://localhost:8000/healthz  # Backend
curl http://localhost:3000          # Frontend

# View logs
tail -f backend.log    # Backend logs (if using start-dev.sh)
tail -f frontend.log   # Frontend logs (if using start-dev.sh)

# Clean restart
pkill -f uvicorn; pkill -f "next-server"
./scripts/start-backend.sh
./scripts/start-frontend.sh
```

## First Time Setup

Only needed once:

```bash
# 1. Install backend dependencies
conda activate dataforge-studio
cd backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# 2. Install frontend dependencies
cd ../frontend
npm install

# 3. Configure environment
cp .env.example .env
# Edit .env with your AWS credentials
```

## URLs

- **Frontend**: <http://localhost:3000>
- **Backend API**: <http://localhost:8000>
- **API Docs**: <http://localhost:8000/v1/docs>
- **Health Check**: <http://localhost:8000/healthz>

## Next Steps

Once everything is running:

1. 📱 Open <http://localhost:3000>
2. 💬 Go to **Chat** tab
3. 📝 Type: "Generate a customer database with 100 users"
4. 📊 Check **Jobs** tab for progress
5. 💾 Check **Downloads** tab to get your files!

## Still Having Issues?

1. Check that conda environment exists:

   ```bash
   conda env list | grep dataforge-studio
   ```

2. Check ports are free:

   ```bash
   lsof -ti:8000  # Backend
   lsof -ti:3000  # Frontend
   ```

3. Check logs for errors:

   ```bash
   # Backend logs
   tail -f backend.log
   
   # Frontend logs  
   tail -f frontend.log
   ```

4. Verify .env file exists and has credentials:

   ```bash
   cat .env | grep AWS
   ```

## Help

If you're still stuck:

- Check the logs for error messages
- Make sure AWS credentials are configured
- Ensure all dependencies are installed
- Try a clean restart (kill all processes, start fresh)

---

**Pro Tip**: Keep both terminals visible side-by-side to monitor logs! 👀
