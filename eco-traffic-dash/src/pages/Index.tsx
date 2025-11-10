import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { motion, AnimatePresence } from "framer-motion";
import io from "socket.io-client";

const API_URL = "http://127.0.0.1:5000";

interface VehicleCounts {
  North: number;
  East: number;
}

interface SignalTimings {
  NorthSouth: number;
  EastWest: number;
}

interface TrafficData {
  vehicle_counts: VehicleCounts;
  signal_timings: SignalTimings;
  total_vehicles: number;
  efficiency_improvement: number;
  current_phase: string;
  active_lane: string;
  last_updated: string;
}

export default function Index() {
  const [data, setData] = useState<TrafficData | null>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [stats, setStats] = useState({ total_vehicles: 0, avg_efficiency: 0, total_cycles: 0 });
  const [northVideoFrame, setNorthVideoFrame] = useState<string | null>(null);
  const [eastVideoFrame, setEastVideoFrame] = useState<string | null>(null);
  const [remainingTime, setRemainingTime] = useState({ North: 0, South: 0, East: 0, West: 0 });

  useEffect(() => {
    // Fetch initial data
    fetchData();
    fetchStats();

    // Set up WebSocket connection
    const socket = io(API_URL);
    
    socket.on("connect", () => {
      console.log("Connected to IntelliFlow server");
    });

    socket.on("update", (updateData: any) => {
      console.log("Received update:", updateData);
      if (updateData.latest) {
        const newData = {
          vehicle_counts: updateData.latest.vehicle_counts || { North: 0, East: 0 },
          signal_timings: updateData.signal_timings || updateData.latest.signal_timings || { NorthSouth: 5, EastWest: 5 },
          total_vehicles: updateData.latest.total_vehicles || 0,
          efficiency_improvement: updateData.latest.efficiency_improvement || 0,
          current_phase: updateData.current_phase || updateData.latest.current_phase || "NorthSouth_Green",
          active_lane: updateData.active_lane || "North",
          last_updated: updateData.time || new Date().toLocaleTimeString(),
        };
        setData(newData);
        // Update remaining times from WebSocket data if available
        if (updateData.remaining_times) {
          setRemainingTime({
            North: Math.max(0, Math.round(updateData.remaining_times.North || 0)),
            South: Math.max(0, Math.round(updateData.remaining_times.South || 0)),
            East: Math.max(0, Math.round(updateData.remaining_times.East || 0)),
            West: Math.max(0, Math.round(updateData.remaining_times.West || 0))
          });
        }
      }
      if (updateData.logs) {
        setLogs(updateData.logs);
      }
    });

    // Poll every 500ms for data updates (faster for real-time traffic lights)
    const interval = setInterval(() => {
      fetchData();
      fetchStats();
    }, 500);

    // Poll for video frames at ~15 FPS for smooth playback
    const videoInterval = setInterval(() => {
      fetchVideoFrames();
    }, 66); // ~15 FPS

    // Update remaining time from API data (fetched every 500ms)
    // No separate interval needed - remaining times come from fetchData()

    // Initial video frame fetch
    fetchVideoFrames();

    return () => {
      socket.disconnect();
      clearInterval(interval);
      if (videoInterval) clearInterval(videoInterval);
    };
  }, [data]);

  const fetchData = async () => {
    try {
      const response = await fetch(`${API_URL}/api/data`);
      const json = await response.json();
      setData(json);
      if (json.logs) {
        setLogs(json.logs);
      }
      // Update remaining times directly from API response
      if (json.remaining_times) {
        setRemainingTime({
          North: Math.max(0, Math.round(json.remaining_times.North || 0)),
          South: Math.max(0, Math.round(json.remaining_times.South || 0)),
          East: Math.max(0, Math.round(json.remaining_times.East || 0)),
          West: Math.max(0, Math.round(json.remaining_times.West || 0))
        });
      }
    } catch (error) {
      console.error("Error fetching data:", error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_URL}/api/stats`);
      const json = await response.json();
      setStats(json);
    } catch (error) {
      console.error("Error fetching stats:", error);
    }
  };

  const fetchVideoFrames = async () => {
    try {
      const response = await fetch(`${API_URL}/api/video/frames`);
      const json = await response.json();
      if (json.north) {
        setNorthVideoFrame(`data:image/jpeg;base64,${json.north}`);
      }
      if (json.east) {
        setEastVideoFrame(`data:image/jpeg;base64,${json.east}`);
      }
    } catch (error) {
      console.error("Error fetching video frames:", error);
    }
  };

  const getLightStatus = (lane: string) => {
    if (!data) return { color: "red", time: 0 };
    const phase = data.current_phase || "All_Red";
    
    // Use remaining times directly from API (updated every 500ms)
    if (lane === "North" || lane === "South") {
      if (phase.includes("NorthSouth_Green")) {
        return { color: "green", time: Math.max(0, Math.round(remainingTime.North)) };
      } else if (phase.includes("NorthSouth_Yellow")) {
        return { color: "yellow", time: Math.max(0, Math.round(remainingTime.North)) };
      } else {
        return { color: "red", time: 0 };
      }
    } else if (lane === "East" || lane === "West") {
      if (phase.includes("EastWest_Green")) {
        return { color: "green", time: Math.max(0, Math.round(remainingTime.East)) };
      } else if (phase.includes("EastWest_Yellow")) {
        return { color: "yellow", time: Math.max(0, Math.round(remainingTime.East)) };
      } else {
        return { color: "red", time: 0 };
      }
    }
    return { color: "red", time: 0 };
  };

  // Prepare chart data
  const vehicleChartData = logs.slice(-10).map((log) => ({
    time: new Date(log.timestamp).toLocaleTimeString(),
    North: log.vehicle_counts?.North || 0,
    East: log.vehicle_counts?.East || 0,
  }));

  const efficiencyChartData = logs.slice(-10).map((log) => ({
    time: new Date(log.timestamp).toLocaleTimeString(),
    Efficiency: log.efficiency_improvement || 0,
  }));

  // Get real vehicle counts from API (South and West are always 0)
  const northCount = data?.vehicle_counts?.North || 0;
  const southCount = 0;  // South count is always 0
  const eastCount = data?.vehicle_counts?.East || 0;
  const westCount = 0;    // West count is always 0

  // Calculate priority score and queue reduction
  const priorityScore = data ? Math.min(10, (data.total_vehicles / 10) + 5).toFixed(1) : "0.0";
  const queueReduction = data ? `-${Math.floor(data.efficiency_improvement / 5)}%` : "0%";

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-white to-blue-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header with IntelliFlow Branding */}
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-8 text-center"
        >
          <motion.div
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="inline-block mb-4"
          >
            <div className="flex items-center justify-center space-x-3">
              <motion.div
                animate={{ rotate: [0, 10, -10, 0] }}
                transition={{ duration: 2, repeat: Infinity, repeatDelay: 3 }}
                className="text-6xl"
              >
                🚦
              </motion.div>
              <div>
                <h1 className="text-6xl font-bold bg-gradient-to-r from-green-600 via-blue-600 to-green-600 bg-clip-text text-transparent mb-2">
                  IntelliFlow
                </h1>
                <div className="h-1 w-32 bg-gradient-to-r from-green-500 to-blue-500 mx-auto rounded-full"></div>
              </div>
            </div>
          </motion.div>
          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="text-xl text-gray-600 font-medium"
          >
            Smart Traffic Control System - AI-Powered Traffic Management Dashboard
          </motion.p>
        </motion.div>

        {/* Live Vehicle Count Section */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mb-8"
        >
          <h2 className="text-2xl font-semibold text-gray-800 mb-4 flex items-center">
            <motion.div 
              className="w-1 h-6 bg-green-500 mr-2"
              animate={{ height: [24, 32, 24] }}
              transition={{ duration: 2, repeat: Infinity }}
            ></motion.div>
            Live Vehicle Count
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[
              { name: "North Lane", count: northCount, color: "blue", highlight: false },
              { name: "South Lane", count: southCount, color: "blue", highlight: false },
              { name: "East Lane", count: eastCount, color: "yellow", highlight: data?.active_lane === "East" || eastCount > northCount },
              { name: "West Lane", count: westCount, color: "blue", highlight: false }
            ].map((lane, index) => (
              <motion.div
                key={lane.name}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4, delay: 0.3 + index * 0.1 }}
                whileHover={{ scale: 1.05, y: -5 }}
              >
                <Card className={`bg-white border-2 ${lane.highlight ? "border-red-500 shadow-lg" : "border-gray-200"} shadow-md transition-all duration-300`}>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center">
                        <motion.span 
                          className="text-3xl mr-3"
                          animate={{ y: [0, -5, 0] }}
                          transition={{ duration: 2, repeat: Infinity, delay: index * 0.2 }}
                        >
                          🚗
                        </motion.span>
                        <div>
                          <p className="font-semibold text-gray-800">{lane.name}</p>
                          <motion.p 
                            key={lane.count}
                            initial={{ scale: 1.2, color: "#10b981" }}
                            animate={{ scale: 1, color: "#111827" }}
                            transition={{ duration: 0.3 }}
                            className="text-2xl font-bold text-gray-900"
                          >
                            {lane.count} vehicles
                          </motion.p>
                        </div>
                      </div>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                      <motion.div 
                        className={`h-3 rounded-full ${
                          lane.color === "yellow" ? "bg-yellow-500" : "bg-blue-500"
                        }`}
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min(100, (lane.count / 50) * 100)}%` }}
                        transition={{ duration: 0.8, delay: 0.5 + index * 0.1 }}
                      ></motion.div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Traffic Light Status Section */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="mb-8"
        >
          <h2 className="text-2xl font-semibold text-gray-800 mb-4 flex items-center">
            <motion.div 
              className="w-1 h-6 bg-green-500 mr-2"
              animate={{ height: [24, 32, 24] }}
              transition={{ duration: 2, repeat: Infinity, delay: 0.5 }}
            ></motion.div>
            Traffic Light Status
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {["North", "South", "East", "West"].map((lane, index) => {
              const status = getLightStatus(lane);
              return (
                <motion.div
                  key={lane}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.5, delay: 0.5 + index * 0.1 }}
                  whileHover={{ scale: 1.05 }}
                >
                  <Card className="bg-white border-gray-200 shadow-md transition-all duration-300">
                    <CardContent className="p-6">
                      <p className="font-semibold text-gray-800 mb-4">{lane} Signal</p>
                      <div className="flex justify-center space-x-2 mb-4">
                        <motion.div 
                          className={`w-12 h-12 rounded-full border-2 border-gray-400 ${
                            status.color === "red" ? "bg-red-500" : "bg-gray-300"
                          }`}
                          animate={status.color === "red" ? { 
                            boxShadow: ["0 0 0px rgba(239, 68, 68, 0)", "0 0 20px rgba(239, 68, 68, 0.8)", "0 0 0px rgba(239, 68, 68, 0)"]
                          } : {}}
                          transition={{ duration: 1.5, repeat: Infinity }}
                        ></motion.div>
                        <motion.div 
                          className={`w-12 h-12 rounded-full border-2 border-gray-400 ${
                            status.color === "yellow" ? "bg-yellow-500" : "bg-gray-300"
                          }`}
                          animate={status.color === "yellow" ? { 
                            boxShadow: ["0 0 0px rgba(234, 179, 8, 0)", "0 0 20px rgba(234, 179, 8, 0.8)", "0 0 0px rgba(234, 179, 8, 0)"]
                          } : {}}
                          transition={{ duration: 1.5, repeat: Infinity }}
                        ></motion.div>
                        <motion.div 
                          className={`w-12 h-12 rounded-full border-2 border-gray-400 ${
                            status.color === "green" ? "bg-green-500" : "bg-gray-300"
                          }`}
                          animate={status.color === "green" ? { 
                            boxShadow: ["0 0 0px rgba(34, 197, 94, 0)", "0 0 20px rgba(34, 197, 94, 0.8)", "0 0 0px rgba(34, 197, 94, 0)"]
                          } : {}}
                          transition={{ duration: 1.5, repeat: Infinity }}
                        ></motion.div>
                      </div>
                      <motion.p 
                        key={`${lane}-${status.time}-${status.color}-${data?.current_phase}`}
                        initial={{ scale: 1.2 }}
                        animate={{ scale: 1 }}
                        className="text-center text-gray-600 font-semibold"
                      >
                        {status.time > 0 ? `${Math.round(status.time)}s remaining` : status.color === "red" ? "0s" : `${Math.round(status.time)}s`}
                      </motion.p>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </div>
        </motion.div>

        {/* AI Decision Logic Section */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.6 }}
          className="mb-8"
        >
          <h2 className="text-2xl font-semibold text-gray-800 mb-4 flex items-center">
            <motion.div 
              className="w-1 h-6 bg-green-500 mr-2"
              animate={{ height: [24, 32, 24] }}
              transition={{ duration: 2, repeat: Infinity, delay: 0.7 }}
            ></motion.div>
            AI Decision Logic
          </h2>
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.7 }}
            whileHover={{ scale: 1.02 }}
          >
            <Card className="bg-white border-gray-200 shadow-lg">
              <CardContent className="p-6">
                <div className="flex items-center justify-center mb-6">
                  <div className="flex items-center space-x-4">
                    <motion.div 
                      className="bg-blue-100 px-6 py-3 rounded-lg"
                      whileHover={{ scale: 1.1, backgroundColor: "#dbeafe" }}
                      transition={{ duration: 0.2 }}
                    >
                      <p className="text-sm text-gray-600">Lane</p>
                      <motion.p 
                        key={data?.current_phase || data?.active_lane}
                        initial={{ x: -10, opacity: 0 }}
                        animate={{ x: 0, opacity: 1 }}
                        className="text-xl font-bold text-gray-800"
                      >
                        {data?.current_phase?.includes("EastWest") ? "East/West Lanes" : "North/South Lanes"}
                      </motion.p>
                    </motion.div>
                    <motion.div 
                      className="text-2xl text-gray-400"
                      animate={{ x: [0, 5, 0] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                    >
                      →
                    </motion.div>
                    <motion.div 
                      className="bg-green-100 px-6 py-3 rounded-lg"
                      whileHover={{ scale: 1.1, backgroundColor: "#dcfce7" }}
                      transition={{ duration: 0.2 }}
                    >
                      <p className="text-sm text-gray-600">Green Light</p>
                      <motion.p 
                        key={`${data?.signal_timings?.NorthSouth}-${data?.signal_timings?.EastWest}-${data?.current_phase}`}
                        initial={{ scale: 1.2, color: "#10b981" }}
                        animate={{ scale: 1, color: "#111827" }}
                        transition={{ duration: 0.3 }}
                        className="text-xl font-bold text-gray-800"
                      >
                        {data?.current_phase?.includes("EastWest") ? `${data?.signal_timings?.EastWest || 0}s` : data?.current_phase?.includes("NorthSouth") ? `${data?.signal_timings?.NorthSouth || 0}s` : "0s"}
                      </motion.p>
                    </motion.div>
                    <motion.div 
                      className="text-2xl text-gray-400"
                      animate={{ x: [0, 5, 0] }}
                      transition={{ duration: 1.5, repeat: Infinity, delay: 0.3 }}
                    >
                      →
                    </motion.div>
                    <motion.div 
                      className="bg-yellow-100 px-6 py-3 rounded-lg"
                      whileHover={{ scale: 1.1, backgroundColor: "#fef9c3" }}
                      transition={{ duration: 0.2 }}
                    >
                      <p className="text-sm text-gray-600">Vehicles</p>
                      <motion.p 
                        key={data?.current_phase?.includes("EastWest") ? eastCount : northCount}
                        initial={{ scale: 1.2, color: "#eab308" }}
                        animate={{ scale: 1, color: "#111827" }}
                        transition={{ duration: 0.3 }}
                        className="text-xl font-bold text-gray-800"
                      >
                        {data?.current_phase?.includes("EastWest") ? eastCount : northCount}
                      </motion.p>
                    </motion.div>
                  </div>
                </div>
                <motion.div 
                  className="bg-gray-50 p-4 rounded-lg mb-4"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.9 }}
                >
                  <p className="text-gray-700">
                    <strong>Analysis:</strong> The {data?.current_phase?.includes("EastWest") ? "east/west" : "north/south"} lanes have {data?.current_phase?.includes("EastWest") ? eastCount : northCount} vehicles, requiring {data?.current_phase?.includes("EastWest") ? `${data?.signal_timings?.EastWest || 0}s` : data?.current_phase?.includes("NorthSouth") ? `${data?.signal_timings?.NorthSouth || 0}s` : "0s"} green time. The AI adjusts timing dynamically based on real-time traffic patterns, reducing congestion by {data?.efficiency_improvement?.toFixed(0) || 0}% compared to fixed-interval signals.
                  </p>
                </motion.div>
                <div className="grid grid-cols-3 gap-4">
                  {[
                    { label: "Priority Score", value: priorityScore, color: "green-600" },
                    { label: "Efficiency", value: `${data?.efficiency_improvement?.toFixed(0) || 0}%`, color: "green-600" },
                    { label: "Queue Reduction", value: queueReduction, color: "blue-600" }
                  ].map((metric, index) => (
                    <motion.div
                      key={metric.label}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 1 + index * 0.1 }}
                      whileHover={{ scale: 1.05, y: -5 }}
                      className="bg-white border border-gray-200 p-4 rounded-lg shadow-sm"
                    >
                      <p className="text-sm text-gray-600 mb-1">{metric.label}</p>
                      <motion.p 
                        key={metric.value}
                        initial={{ scale: 1.2 }}
                        animate={{ scale: 1 }}
                        className={`text-2xl font-bold text-${metric.color}`}
                      >
                        {metric.value}
                      </motion.p>
                    </motion.div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>

        {/* Performance Analytics */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.8 }}
          className="mb-8"
        >
          <h2 className="text-2xl font-semibold text-gray-800 mb-4 flex items-center">
            <motion.div 
              className="w-1 h-6 bg-green-500 mr-2"
              animate={{ height: [24, 32, 24] }}
              transition={{ duration: 2, repeat: Infinity, delay: 0.9 }}
            ></motion.div>
            Performance Analytics
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.9 }}
              whileHover={{ scale: 1.02 }}
            >
              <Card className="bg-white border-gray-200 shadow-md">
                <CardHeader>
                  <CardTitle className="text-gray-800 flex items-center">
                    <motion.span 
                      className="mr-2"
                      animate={{ rotate: [0, 10, -10, 0] }}
                      transition={{ duration: 2, repeat: Infinity, repeatDelay: 2 }}
                    >
                      📈
                    </motion.span>
                    Traffic Flow (24h)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={vehicleChartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="time" stroke="#6b7280" />
                      <YAxis stroke="#6b7280" />
                      <Tooltip contentStyle={{ backgroundColor: "#ffffff", border: "1px solid #e5e7eb" }} />
                      <Legend />
                      <Line type="monotone" dataKey="North" stroke="#3b82f6" strokeWidth={2} name="North" />
                      <Line type="monotone" dataKey="East" stroke="#10b981" strokeWidth={2} name="East" />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 1 }}
              whileHover={{ scale: 1.02 }}
            >
              <Card className="bg-white border-gray-200 shadow-md">
                <CardHeader>
                  <CardTitle className="text-gray-800 flex items-center">
                    <motion.span 
                      className="mr-2"
                      animate={{ rotate: [0, -15, 15, 0] }}
                      transition={{ duration: 2, repeat: Infinity, repeatDelay: 2 }}
                    >
                      ⏱️
                    </motion.span>
                    Average Waiting Time (seconds)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={[
                      { direction: "North", traditional: 85, ai: 30 },
                      { direction: "South", traditional: 75, ai: 28 },
                      { direction: "East", traditional: 90, ai: 35 },
                      { direction: "West", traditional: 78, ai: 28 }
                    ]}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="direction" stroke="#6b7280" />
                      <YAxis stroke="#6b7280" />
                      <Tooltip contentStyle={{ backgroundColor: "#ffffff", border: "1px solid #e5e7eb" }} />
                      <Legend />
                      <Bar dataKey="traditional" fill="#9ca3af" name="Traditional System" />
                      <Bar dataKey="ai" fill="#10b981" name="AI-Optimized" />
                    </BarChart>
                  </ResponsiveContainer>
                  <motion.p 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 1.2 }}
                    className="text-center mt-4 text-green-600 font-semibold"
                  >
                    {data?.efficiency_improvement?.toFixed(0) || 62}% reduction in average waiting time with AI optimization
                  </motion.p>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </motion.div>

        {/* Live Video Feeds */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 1 }}
          className="mb-8"
        >
          <h2 className="text-2xl font-semibold text-gray-800 mb-4 flex items-center">
            <motion.div 
              className="w-1 h-6 bg-green-500 mr-2"
              animate={{ height: [24, 32, 24] }}
              transition={{ duration: 2, repeat: Infinity, delay: 1.1 }}
            ></motion.div>
            Live Video Feeds
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 1.1 }}
              whileHover={{ scale: 1.02 }}
            >
              <Card className="bg-white border-gray-200 shadow-md">
                <CardHeader>
                  <CardTitle className="text-gray-800">North Lane - Live Detection</CardTitle>
                </CardHeader>
                <CardContent>
                  <motion.div 
                    className="relative bg-black rounded-lg overflow-hidden mb-4"
                    style={{ aspectRatio: "16/9" }}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.5 }}
                  >
                    <AnimatePresence mode="wait">
                      {northVideoFrame ? (
                        <motion.img 
                          key="north-video"
                          src={northVideoFrame}
                          alt="North Lane Video"
                          className="w-full h-full object-contain"
                          style={{ imageRendering: "auto" }}
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          exit={{ opacity: 0 }}
                          transition={{ duration: 0.3 }}
                        />
                      ) : (
                        <motion.div 
                          key="north-loading"
                          className="w-full h-full flex items-center justify-center"
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          exit={{ opacity: 0 }}
                        >
                          <motion.p 
                            animate={{ opacity: [0.5, 1, 0.5] }}
                            transition={{ duration: 1.5, repeat: Infinity }}
                            className="text-white"
                          >
                            Loading North Lane video...
                          </motion.p>
                        </motion.div>
                      )}
                    </AnimatePresence>
                    <motion.div 
                      className="absolute top-2 left-2 bg-green-600 bg-opacity-90 px-3 py-1 rounded"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 1.3, type: "spring" }}
                    >
                      <motion.span 
                        key={northCount}
                        initial={{ scale: 1.2 }}
                        animate={{ scale: 1 }}
                        className="text-white font-bold text-lg"
                      >
                        Vehicles: {northCount}
                      </motion.span>
                    </motion.div>
                  </motion.div>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 1.2 }}
              whileHover={{ scale: 1.02 }}
            >
              <Card className="bg-white border-gray-200 shadow-md">
                <CardHeader>
                  <CardTitle className="text-gray-800">East Lane - Live Detection</CardTitle>
                </CardHeader>
                <CardContent>
                  <motion.div 
                    className="relative bg-black rounded-lg overflow-hidden mb-4"
                    style={{ aspectRatio: "16/9" }}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.5 }}
                  >
                    <AnimatePresence mode="wait">
                      {eastVideoFrame ? (
                        <motion.img 
                          key="east-video"
                          src={eastVideoFrame}
                          alt="East Lane Video"
                          className="w-full h-full object-contain"
                          style={{ imageRendering: "auto" }}
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          exit={{ opacity: 0 }}
                          transition={{ duration: 0.3 }}
                        />
                      ) : (
                        <motion.div 
                          key="east-loading"
                          className="w-full h-full flex items-center justify-center"
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          exit={{ opacity: 0 }}
                        >
                          <motion.p 
                            animate={{ opacity: [0.5, 1, 0.5] }}
                            transition={{ duration: 1.5, repeat: Infinity }}
                            className="text-white"
                          >
                            Loading East Lane video...
                          </motion.p>
                        </motion.div>
                      )}
                    </AnimatePresence>
                    <motion.div 
                      className="absolute top-2 left-2 bg-blue-600 bg-opacity-90 px-3 py-1 rounded"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 1.4, type: "spring" }}
                    >
                      <motion.span 
                        key={eastCount}
                        initial={{ scale: 1.2 }}
                        animate={{ scale: 1 }}
                        className="text-white font-bold text-lg"
                      >
                        Vehicles: {eastCount}
                      </motion.span>
                    </motion.div>
                  </motion.div>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
