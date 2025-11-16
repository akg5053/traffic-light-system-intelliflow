"use client";

import { useState, useEffect } from "react";

// Configuration - Update this with your Flask server URL
// For local development: http://127.0.0.1:5000
// For production: Replace with your deployed Flask server URL or ngrok tunnel
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:5000";

// Optional: Set this environment variable for authentication
const AUTH_SECRET = process.env.NEXT_PUBLIC_EVP_SECRET || null;

interface EvpState {
  active: boolean;
  lane: string | null;
  started_at: number | null;
  eta_seconds: number | null;
  expected_arrival_ts: number | null;
  remaining_seconds?: number;
}

export default function EvpRemote() {
  const [selectedLane, setSelectedLane] = useState<string | null>(null);
  const [etaSeconds, setEtaSeconds] = useState<number>(60);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [currentState, setCurrentState] = useState<EvpState | null>(null);

  const lanes = [
    { id: "N", name: "North", emoji: "⬆️" },
    { id: "E", name: "East", emoji: "➡️" },
    { id: "S", name: "South", emoji: "⬇️" },
    { id: "W", name: "West", emoji: "⬅️" },
  ];

  const etaOptions = [30, 45, 60, 90, 120];

  // Fetch current EVP state on mount
  useEffect(() => {
    fetchEvpState();
    const interval = setInterval(fetchEvpState, 2000); // Poll every 2 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchEvpState = async () => {
    try {
      const response = await fetch(`${API_URL}/api/evp/state`);
      if (response.ok) {
        const state = await response.json();
        setCurrentState(state);
      }
    } catch (err) {
      // Silently fail - server might not be available
    }
  };

  const handleStartEvp = async () => {
    if (!selectedLane) {
      setError("Please select a lane");
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const headers: HeadersInit = {
        "Content-Type": "application/json",
      };
      
      if (AUTH_SECRET) {
        headers["X-Auth"] = AUTH_SECRET;
      }

      const response = await fetch(`${API_URL}/api/evp/start`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          lane: selectedLane,
          eta_seconds: etaSeconds,
        }),
      });

      const data = await response.json();

      if (response.ok && data.ok) {
        setSuccess(`Emergency vehicle preemption started for ${lanes.find(l => l.id === selectedLane)?.name} lane`);
        setCurrentState(data.state);
        // Clear success message after 3 seconds
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError(data.error || "Failed to start EVP");
      }
    } catch (err) {
      setError("Failed to connect to server. Make sure the Flask server is running.");
    } finally {
      setLoading(false);
    }
  };

  const handleClearEvp = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const headers: HeadersInit = {
        "Content-Type": "application/json",
      };
      
      if (AUTH_SECRET) {
        headers["X-Auth"] = AUTH_SECRET;
      }

      const response = await fetch(`${API_URL}/api/evp/clear`, {
        method: "POST",
        headers,
      });

      const data = await response.json();

      if (response.ok && data.ok) {
        setSuccess("Emergency vehicle preemption cleared - returning to normal operation");
        setCurrentState(data.state);
        setSelectedLane(null);
        // Clear success message after 3 seconds
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError(data.error || "Failed to clear EVP");
      }
    } catch (err) {
      setError("Failed to connect to server. Make sure the Flask server is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50 via-orange-50 to-yellow-50 p-4">
      <div className="max-w-md mx-auto">
        {/* Header */}
        <div className="text-center mb-8 pt-8">
          <div className="text-6xl mb-4">🚑</div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Emergency Vehicle Preemption
          </h1>
          <p className="text-gray-600">
            Remote Control System
          </p>
        </div>

        {/* Current Status */}
        {currentState && currentState.active && (
          <div className="bg-red-600 text-white rounded-lg p-4 mb-6 shadow-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-lg">Active Emergency</p>
                <p className="text-sm opacity-90">
                  {currentState.lane} Lane - {Math.round(currentState.remaining_seconds || 0)}s remaining
                </p>
              </div>
              <div className="text-3xl">🚨</div>
            </div>
          </div>
        )}

        {/* Error/Success Messages */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg mb-4">
            {error}
          </div>
        )}
        {success && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg mb-4">
            {success}
          </div>
        )}

        {/* Lane Selection */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            Select Emergency Vehicle Lane
          </h2>
          <div className="grid grid-cols-2 gap-3">
            {lanes.map((lane) => (
              <button
                key={lane.id}
                onClick={() => setSelectedLane(lane.id)}
                disabled={loading}
                className={`p-4 rounded-lg border-2 transition-all ${
                  selectedLane === lane.id
                    ? "border-red-600 bg-red-50 scale-105"
                    : "border-gray-200 bg-gray-50 hover:border-gray-300"
                } ${loading ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                <div className="text-3xl mb-2">{lane.emoji}</div>
                <div className="font-semibold text-gray-800">{lane.name}</div>
              </button>
            ))}
          </div>
        </div>

        {/* ETA Selection */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            Estimated Time of Arrival (seconds)
          </h2>
          <div className="flex flex-wrap gap-2">
            {etaOptions.map((eta) => (
              <button
                key={eta}
                onClick={() => setEtaSeconds(eta)}
                disabled={loading}
                className={`px-4 py-2 rounded-lg border-2 transition-all ${
                  etaSeconds === eta
                    ? "border-blue-600 bg-blue-50 text-blue-700 font-semibold"
                    : "border-gray-200 bg-gray-50 text-gray-700 hover:border-gray-300"
                } ${loading ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                {eta}s
              </button>
            ))}
          </div>
          <div className="mt-4">
            <label className="block text-sm text-gray-600 mb-2">
              Custom ETA (10-300 seconds)
            </label>
            <input
              type="number"
              min="10"
              max="300"
              value={etaSeconds}
              onChange={(e) => setEtaSeconds(parseInt(e.target.value) || 60)}
              disabled={loading}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="space-y-3">
          <button
            onClick={handleStartEvp}
            disabled={loading || !selectedLane}
            className={`w-full py-4 rounded-lg font-semibold text-white text-lg shadow-lg transition-all ${
              loading || !selectedLane
                ? "bg-gray-400 cursor-not-allowed"
                : "bg-red-600 hover:bg-red-700 active:scale-95"
            }`}
          >
            {loading ? "Processing..." : "🚑 Start Emergency Preemption"}
          </button>

          <button
            onClick={handleClearEvp}
            disabled={loading || !currentState?.active}
            className={`w-full py-4 rounded-lg font-semibold text-white text-lg shadow-lg transition-all ${
              loading || !currentState?.active
                ? "bg-gray-400 cursor-not-allowed"
                : "bg-green-600 hover:bg-green-700 active:scale-95"
            }`}
          >
            ✅ Clear / Back to Normal
          </button>
        </div>

        {/* Info Footer */}
        <div className="mt-8 text-center text-sm text-gray-500">
          <p>IntelliFlow Traffic Management System</p>
          <p className="mt-1">Server: {API_URL}</p>
        </div>
      </div>
    </div>
  );
}
