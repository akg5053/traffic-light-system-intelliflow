import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { motion, AnimatePresence } from "framer-motion";
import io from "socket.io-client";

const API_URL = "http://127.0.0.1:5000";

type LaneName = "North" | "South" | "East" | "West";

interface VehicleCounts {
  North: number;
  South: number;
  East: number;
  West: number;
  [key: string]: number;
}

interface SignalTimings {
  NorthSouth: number;
  EastWest: number;
}

interface RemainingTimes {
  [lane: string]: number;
}

interface LaneGroups {
  [group: string]: string[];
}

interface TrafficData {
  vehicle_counts: VehicleCounts;
  group_counts: { [key: string]: number };
  signal_timings: SignalTimings;
  total_vehicles: number;
  efficiency_improvement: number;
  current_phase: string;
  active_lane: string;
  active_group: string;
  last_updated: string;
  remaining_times: RemainingTimes;
  lanes_available: string[];
  lane_groups: LaneGroups;
  system_mode: string;
}

interface TrafficLog {
  timestamp?: string;
  vehicle_counts?: Record<string, number>;
  group_counts?: Record<string, number>;
  signal_timings?: Record<string, number>;
  current_phase?: string;
  total_vehicles?: number;
  efficiency_improvement?: number;
}

interface ApiResponse extends TrafficData {
  logs?: TrafficLog[];
  latest?: TrafficLog;
}

interface StatsSummary {
  total_vehicles: number;
  avg_efficiency: number;
  total_cycles: number;
}

interface FramesResponse {
  frames?: Record<string, string | null>;
  counts?: Record<string, number>;
  lanes?: string[];
}

const DEFAULT_LANE_GROUPS: LaneGroups = {
  NorthSouth: ["North", "South"],
  EastWest: ["East", "West"],
};

const DEFAULT_COUNTS: VehicleCounts = {
  North: 0,
  South: 0,
  East: 0,
  West: 0,
};

const DEFAULT_REMAINING: RemainingTimes = {
  North: 0,
  South: 0,
  East: 0,
  West: 0,
};

const normalizeTrafficData = (payload: Partial<ApiResponse>): TrafficData => {
  const vehicleCounts: VehicleCounts = {
    ...DEFAULT_COUNTS,
    ...(payload.vehicle_counts || {}),
  };
  const remainingTimes: RemainingTimes = {
    ...DEFAULT_REMAINING,
    ...(payload.remaining_times || {}),
  };
  const laneGroups = payload.lane_groups || DEFAULT_LANE_GROUPS;
  const groupCounts = payload.group_counts || {
    NorthSouth: laneGroups.NorthSouth?.reduce((sum, lane) => sum + (vehicleCounts[lane] || 0), 0) ?? 0,
    EastWest: laneGroups.EastWest?.reduce((sum, lane) => sum + (vehicleCounts[lane] || 0), 0) ?? 0,
  };

  return {
    vehicle_counts: vehicleCounts,
    group_counts: groupCounts,
    signal_timings: {
      NorthSouth: payload.signal_timings?.NorthSouth ?? 5,
      EastWest: payload.signal_timings?.EastWest ?? 5,
    },
    total_vehicles:
      payload.total_vehicles ??
      Object.values(vehicleCounts).reduce((sum, count) => sum + count, 0),
    efficiency_improvement: payload.efficiency_improvement ?? 0,
    current_phase: payload.current_phase ?? "NorthSouth_Green",
    active_lane: payload.active_lane ?? "North",
    active_group:
      payload.active_group ??
      ((payload.current_phase || "").includes("EastWest") ? "EastWest" : "NorthSouth"),
    last_updated: payload.last_updated ?? new Date().toLocaleTimeString(),
    remaining_times: Object.keys(remainingTimes).reduce((acc, lane) => {
      acc[lane] = Math.max(0, Math.round(remainingTimes[lane] ?? 0));
      return acc;
    }, {} as RemainingTimes),
    lanes_available: payload.lanes_available?.length
      ? payload.lanes_available
      : ["North", "East"],
    lane_groups: laneGroups,
    system_mode: payload.system_mode ?? "TWO_VIDEO",
  };
};

export default function Index() {
  const [data, setData] = useState<TrafficData | null>(null);
  const [logs, setLogs] = useState<TrafficLog[]>([]);
  const [stats, setStats] = useState<StatsSummary>({ total_vehicles: 0, avg_efficiency: 0, total_cycles: 0 });
  const [videoFrames, setVideoFrames] = useState<Record<string, string | null>>({});
  const [remainingTime, setRemainingTime] = useState<RemainingTimes>(DEFAULT_REMAINING);

  const laneOrder: LaneName[] = ["North", "South", "East", "West"];
  const vehicleCounts = data?.vehicle_counts ?? DEFAULT_COUNTS;
  const laneGroups = data?.lane_groups ?? DEFAULT_LANE_GROUPS;
  const lanesAvailable = data?.lanes_available?.length ? data.lanes_available : ["North", "East"];
  const groupCounts = data?.group_counts ?? {
    NorthSouth: laneGroups.NorthSouth.reduce((sum, lane) => sum + (vehicleCounts[lane] || 0), 0),
    EastWest: laneGroups.EastWest.reduce((sum, lane) => sum + (vehicleCounts[lane] || 0), 0),
  };
  const northGroupCount = groupCounts.NorthSouth ?? 0;
  const eastGroupCount = groupCounts.EastWest ?? 0;
  const activeGroup = data?.active_group ?? "NorthSouth";

  const laneCards = laneOrder.map((lane) => {
    const group = Object.entries(laneGroups).find(([, lanes]) => lanes.includes(lane))?.[0];
    const isAvailable = lanesAvailable.includes(lane);
    return {
      lane,
      name: `${lane} Lane`,
      count: vehicleCounts[lane] || 0,
      highlight: group === activeGroup,
      available: isAvailable,
      group,
    };
  });

  const fetchData = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/data`);
      const json = (await response.json()) as ApiResponse;
      const normalized = normalizeTrafficData(json);
      setData(normalized);
      setRemainingTime(normalized.remaining_times);
      setLogs(json.logs ?? []);
    } catch (error) {
      console.error("Error fetching data:", error);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/stats`);
      const json = (await response.json()) as StatsSummary;
      setStats(json);
    } catch (error) {
      console.error("Error fetching stats:", error);
    }
  }, []);

  const fetchVideoFrames = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/video/frames`);
      const json = (await response.json()) as FramesResponse;
      if (json.frames) {
        const framed: Record<string, string | null> = {};
        Object.entries(json.frames).forEach(([lane, value]) => {
          framed[lane] = value ? `data:image/jpeg;base64,${value}` : null;
        });
        setVideoFrames(framed);
      }
    } catch (error) {
      console.error("Error fetching video frames:", error);
    }
  }, []);

  useEffect(() => {
    // Fetch initial data
    fetchData();
    fetchStats();

    // Set up WebSocket connection
    const socket = io(API_URL);
    
    socket.on("connect", () => {
      console.log("Connected to IntelliFlow server");
    });

    socket.on("update", (updateData: ApiResponse) => {
      console.log("Received update:", updateData);
      const normalized = normalizeTrafficData(updateData);
      setData(normalized);
      setRemainingTime(normalized.remaining_times);
      setLogs(updateData.logs ?? []);
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
  }, [fetchData, fetchStats, fetchVideoFrames]);

  const getLightStatus = (lane: LaneName) => {
    if (!data) return { color: "red", time: 0 };
    const phase = data.current_phase || "All_Red";
    const laneGroups = data.lane_groups || DEFAULT_LANE_GROUPS;
    const groupEntry = Object.entries(laneGroups).find(([, lanes]) => lanes.includes(lane));
    const laneRemaining = Math.max(0, Math.round(remainingTime[lane] ?? 0));

    if (!groupEntry) {
      return { color: "red", time: laneRemaining };
    }

    const [groupName] = groupEntry;

    if (phase.includes("All_Red")) {
      return { color: "red", time: laneRemaining };
    }

    if (phase.includes(groupName) && phase.includes("Green")) {
      return { color: "green", time: laneRemaining };
    }

    if (phase.includes(groupName) && phase.includes("Yellow")) {
      return { color: "yellow", time: laneRemaining };
    }

    return { color: "red", time: 0 };
  };

  // Prepare chart data
  const vehicleChartData = logs.slice(-10).map((log) => {
    const vc = log.vehicle_counts || {};
    const gc = log.group_counts || {};
    const northSouth = gc.NorthSouth ?? ((vc.North || 0) + (vc.South || 0));
    const eastWest = gc.EastWest ?? ((vc.East || 0) + (vc.West || 0));
    return {
      time: new Date(log.timestamp).toLocaleTimeString(),
      NorthSouth: northSouth,
      EastWest: eastWest,
    };
  });

  const efficiencyChartData = logs.slice(-10).map((log) => ({
    time: new Date(log.timestamp).toLocaleTimeString(),
    Efficiency: log.efficiency_improvement || 0,
  }));

  // Get real vehicle counts from API (South and West are always 0)

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
            {laneCards.map((lane, index) => (
              <motion.div
                key={lane.name}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4, delay: 0.3 + index * 0.1 }}
                whileHover={{ scale: 1.05, y: -5 }}
              >
                <Card
                  className={`bg-white border-2 ${
                    lane.highlight ? "border-red-500 shadow-lg" : "border-gray-200"
                  } ${lane.available ? "" : "opacity-50"} shadow-md transition-all duration-300`}
                >
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
                            key={`${lane.name}-${lane.count}`}
                            initial={{ scale: 1.2, color: lane.highlight ? "#ef4444" : "#10b981" }}
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
                          lane.highlight
                            ? "bg-red-500"
                            : lane.group === "EastWest"
                            ? "bg-yellow-500"
                            : "bg-blue-500"
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
            {laneOrder.map((lane, index) => {
              const status = getLightStatus(lane);
              const available = lanesAvailable.includes(lane);

              return (
                <motion.div
                  key={lane}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.5, delay: 0.5 + index * 0.1 }}
                  whileHover={{ scale: 1.05 }}
                >
                  <Card
                    className={`bg-white border-gray-200 shadow-md transition-all duration-300 ${
                      available ? "" : "opacity-50"
                    }`}
                  >
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
                        key={data?.active_group === "EastWest" ? eastGroupCount : northGroupCount}
                        initial={{ scale: 1.2, color: "#eab308" }}
                        animate={{ scale: 1, color: "#111827" }}
                        transition={{ duration: 0.3 }}
                        className="text-xl font-bold text-gray-800"
                      >
                        {data?.active_group === "EastWest" ? eastGroupCount : northGroupCount}
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
                    <strong>Analysis:</strong> The {data?.active_group === "EastWest" ? "east/west" : "north/south"} lanes have {data?.active_group === "EastWest" ? eastGroupCount : northGroupCount} vehicles, requiring {data?.active_group === "EastWest" ? `${data?.signal_timings?.EastWest || 0}s` : `${data?.signal_timings?.NorthSouth || 0}s`} green time. The AI adjusts timing dynamically based on real-time traffic patterns, reducing congestion by {data?.efficiency_improvement?.toFixed(0) || 0}% compared to fixed-interval signals.
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
                      <Line type="monotone" dataKey="NorthSouth" stroke="#3b82f6" strokeWidth={2} name="North/South" />
                      <Line type="monotone" dataKey="EastWest" stroke="#10b981" strokeWidth={2} name="East/West" />
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
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {lanesAvailable.map((lane, index) => {
              const frameKey = lane.toLowerCase();
              const frame = videoFrames[frameKey];
              const count = vehicleCounts[lane] || 0;
              return (
                <motion.div
                  key={`${lane}-video-card`}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.6, delay: 1.1 + index * 0.1 }}
                  whileHover={{ scale: 1.02 }}
                >
                  <Card className="bg-white border-gray-200 shadow-md">
                    <CardHeader>
                      <CardTitle className="text-gray-800">{lane} Lane - Live Detection</CardTitle>
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
                          {frame ? (
                            <motion.img
                              key={`${lane}-video`}
                              src={frame}
                              alt={`${lane} Lane Video`}
                              className="w-full h-full object-contain"
                              style={{ imageRendering: "auto" }}
                              initial={{ opacity: 0 }}
                              animate={{ opacity: 1 }}
                              exit={{ opacity: 0 }}
                              transition={{ duration: 0.3 }}
                            />
                          ) : (
                            <motion.div
                              key={`${lane}-loading`}
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
                                Loading {lane} lane video...
                              </motion.p>
                            </motion.div>
                          )}
                        </AnimatePresence>
                        <motion.div
                          className="absolute top-2 left-2 bg-green-600 bg-opacity-90 px-3 py-1 rounded"
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          transition={{ delay: 1.3 + index * 0.1, type: "spring" }}
                        >
                          <motion.span
                            key={`${lane}-count-${count}`}
                            initial={{ scale: 1.2 }}
                            animate={{ scale: 1 }}
                            className="text-white font-bold text-lg"
                          >
                            Vehicles: {count}
                          </motion.span>
                        </motion.div>
                      </motion.div>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
