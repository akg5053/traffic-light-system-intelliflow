# Emergency Vehicle Preemption (EVP) Remote Control

A mobile-friendly Next.js web application for remotely triggering emergency vehicle preemption on the IntelliFlow traffic management system.

## Features

- 🚑 One-click emergency vehicle preemption activation
- 📱 Mobile-optimized interface
- 🎯 Select lane (North, South, East, West)
- ⏱️ Configurable ETA (10-300 seconds)
- ✅ Clear/Reset functionality
- 🔄 Real-time status updates

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure API URL:**
   
   Create a `.env.local` file in the `evp-remote` directory:
   ```env
   NEXT_PUBLIC_API_URL=http://127.0.0.1:5000
   NEXT_PUBLIC_EVP_SECRET=your-secret-key-here  # Optional, for authentication
   ```

   - For local development: `http://127.0.0.1:5000`
   - For production: Use your deployed Flask server URL or ngrok tunnel

3. **Run development server:**
   ```bash
   npm run dev
   ```

   The app will be available at `http://localhost:3000`

## Deployment to Vercel

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Add EVP remote app"
   git push
   ```

2. **Deploy to Vercel:**
   - Go to [vercel.com](https://vercel.com)
   - Import your GitHub repository
   - Set environment variables:
     - `NEXT_PUBLIC_API_URL`: Your Flask server URL (or ngrok tunnel)
     - `NEXT_PUBLIC_EVP_SECRET`: (Optional) Your authentication secret
   - Deploy!

3. **Update Flask CORS:**
   
   Make sure your Flask server (`ml_model/dashboard.py`) allows requests from your Vercel domain:
   ```python
   CORS(app, origins=["https://your-app.vercel.app"])
   ```

## Usage

1. Open the app on your mobile device or browser
2. Select the lane from which the emergency vehicle is approaching
3. Set the estimated time of arrival (ETA) in seconds
4. Tap "🚑 Start Emergency Preemption"
5. The system will adjust traffic light timings to prioritize the emergency vehicle
6. Tap "✅ Clear / Back to Normal" when the emergency has passed

## API Endpoints

The app communicates with the Flask backend at:
- `POST /api/evp/start` - Start emergency preemption
- `POST /api/evp/clear` - Clear emergency preemption
- `GET /api/evp/state` - Get current EVP state

## Environment Variables

- `NEXT_PUBLIC_API_URL`: Flask server URL (default: `http://127.0.0.1:5000`)
- `NEXT_PUBLIC_EVP_SECRET`: Optional authentication secret (if configured in Flask)

## Notes

- The app polls the server every 2 seconds to get the current EVP state
- If authentication is enabled in Flask, set `NEXT_PUBLIC_EVP_SECRET` to match
- For production, use HTTPS and secure your API endpoints
