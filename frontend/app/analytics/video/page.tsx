'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { API_URL } from '@/lib/api';

interface Camera {
  id: string;
  name: string;
  location: string;
  status: 'online' | 'offline' | 'warning';
  fps: number;
  resolution: string;
  last_event?: string;
}

interface VideoEvent {
  id: string;
  timestamp: string;
  camera: string;
  type: 'crowd_detected' | 'wait_time' | 'safety_violation' | 'queue_alert' | 'occupancy';
  severity: 'info' | 'warning' | 'critical';
  description: string;
  details: string;
  snapshot?: string;
}

interface VideoStats {
  total_cameras: number;
  active_cameras: number;
  avg_occupancy: number;
  peak_occupancy: number;
  avg_wait_time: number;
  events_today: number;
  occupancy_by_hour: { hour: number; occupancy: number }[];
  wait_times_by_area: { area: string; avg_wait: number; current_wait: number }[];
  crowd_density: { time: string; density: number }[];
}

export default function AnalyticsVideoPage() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [events, setEvents] = useState<VideoEvent[]>([]);
  const [stats, setStats] = useState<VideoStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCamera, setSelectedCamera] = useState<string>('all');

  useEffect(() => {
    loadVideoData();
  }, []);

  const loadVideoData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/analytics/video`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setCameras(data.cameras || []);
        setEvents(data.events || []);
        setStats(data.stats);
      } else {
        console.error('Failed to load video analytics data');
        setCameras([]);
        setEvents([]);
        setStats(null);
      }
    } catch (error) {
      console.error('Error loading video analytics data:', error);
      setCameras([]);
      setEvents([]);
      setStats(null);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online': return 'success';
      case 'warning': return 'warning';
      case 'offline': return 'error';
      default: return 'surface';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'error';
      case 'warning': return 'warning';
      case 'info': return 'primary';
      default: return 'surface';
    }
  };

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'crowd_detected': return '👥';
      case 'wait_time': return '⏱️';
      case 'safety_violation': return '⚠️';
      case 'queue_alert': return '📋';
      case 'occupancy': return '🏢';
      default: return '📹';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">📹</div>
          <h2 className="text-2xl font-bold text-surface-900 mb-2">No Video Analytics Data</h2>
          <p className="text-surface-600 mb-4">Unable to load video analytics data. Please try again later.</p>
          <button
            onClick={loadVideoData}
            className="px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/analytics" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
          <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <div className="flex-1">
          <h1 className="text-3xl font-display font-bold text-surface-900">Video Analytics</h1>
          <p className="text-surface-500 mt-1">AI-powered camera feeds and crowd analysis</p>
        </div>
        <button className="px-4 py-2 bg-primary-500 text-gray-900 rounded-lg hover:bg-primary-600 transition-colors text-sm font-medium flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          View Live Feeds
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-br from-success-50 to-success-100 rounded-2xl p-6 border border-success-200"
        >
          <div className="text-success-600 text-sm font-semibold mb-1">Active Cameras</div>
          <div className="text-3xl font-bold text-success-900">
            {stats?.active_cameras || 0}/{stats?.total_cameras || 0}
          </div>
          <div className="text-success-600 text-xs mt-1">System operational</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gradient-to-br from-primary-50 to-primary-100 rounded-2xl p-6 border border-primary-200"
        >
          <div className="text-primary-600 text-sm font-semibold mb-1">Current Occupancy</div>
          <div className="text-3xl font-bold text-primary-900">
            {stats?.avg_occupancy || 0}%
          </div>
          <div className="text-primary-600 text-xs mt-1">Average across areas</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-gradient-to-br from-accent-50 to-accent-100 rounded-2xl p-6 border border-accent-200"
        >
          <div className="text-accent-600 text-sm font-semibold mb-1">Avg Wait Time</div>
          <div className="text-3xl font-bold text-accent-900">
            {stats?.avg_wait_time || 0} min
          </div>
          <div className="text-accent-600 text-xs mt-1">Across all zones</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-gradient-to-br from-warning-50 to-warning-100 rounded-2xl p-6 border border-warning-200"
        >
          <div className="text-warning-600 text-sm font-semibold mb-1">Events Today</div>
          <div className="text-3xl font-bold text-warning-900">
            {stats?.events_today || 0}
          </div>
          <div className="text-warning-600 text-xs mt-1">AI detections</div>
        </motion.div>
      </div>

      {/* Camera Grid */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white rounded-2xl p-6 shadow-sm border border-surface-100"
      >
        <h3 className="text-xl font-semibold text-surface-900 mb-4">Camera Status</h3>
        <div className="grid grid-cols-3 gap-4">
          {cameras.map((camera, i) => {
            const statusColor = getStatusColor(camera.status);
            return (
              <motion.div
                key={camera.id}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.05 }}
                className="border-2 border-surface-200 rounded-xl p-4 hover:border-primary-300 hover:shadow-md transition-all cursor-pointer"
              >
                {/* Camera Preview Placeholder */}
                <div className="aspect-video bg-gradient-to-br from-surface-800 to-surface-900 rounded-lg mb-3 flex items-center justify-center relative overflow-hidden">
                  <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZGVmcz48cGF0dGVybiBpZD0iZ3JpZCIgd2lkdGg9IjQwIiBoZWlnaHQ9IjQwIiBwYXR0ZXJuVW5pdHM9InVzZXJTcGFjZU9uVXNlIj48cGF0aCBkPSJNIDQwIDAgTCAwIDAgMCA0MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLW9wYWNpdHk9IjAuMSIgc3Ryb2tlLXdpZHRoPSIxIi8+PC9wYXR0ZXJuPjwvZGVmcz48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSJ1cmwoI2dyaWQpIi8+PC9zdmc+')] opacity-30"></div>
                  <div className="relative z-10 text-center">
                    <div className="text-4xl mb-2">📹</div>
                    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-${statusColor}-100 text-${statusColor}-700 text-xs font-semibold`}>
                      <span className={`w-1.5 h-1.5 rounded-full bg-${statusColor}-500 ${camera.status === 'online' ? 'animate-pulse' : ''}`}></span>
                      {camera.status.toUpperCase()}
                    </div>
                  </div>
                  {camera.status === 'online' && (
                    <div className="absolute top-2 right-2 px-2 py-1 bg-white/70 text-gray-900 text-xs rounded">
                      REC ●
                    </div>
                  )}
                </div>

                {/* Camera Info */}
                <div className="space-y-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-semibold text-surface-900">{camera.name}</h4>
                      <p className="text-xs text-surface-500">{camera.location}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-surface-600">
                    <span>{camera.resolution}</span>
                    <span>{camera.fps} FPS</span>
                    {camera.last_event && (
                      <span className="text-primary-600">{camera.last_event}</span>
                    )}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </motion.div>

      {/* Analytics Row */}
      <div className="grid grid-cols-3 gap-6">
        {/* Occupancy Chart */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="bg-white rounded-2xl p-6 shadow-sm border border-surface-100"
        >
          <h3 className="text-xl font-semibold text-surface-900 mb-4">Occupancy by Hour</h3>
          <div className="flex items-end justify-between h-48 gap-1">
            {stats?.occupancy_by_hour.map((item, i) => {
              const percentage = item.occupancy;
              const isHigh = percentage > 80;
              const isMedium = percentage > 60;

              return (
                <div key={i} className="flex flex-col items-center flex-1">
                  <div
                    className={`w-full rounded-t-sm transition-all ${
                      isHigh
                        ? 'bg-gradient-to-t from-error-500 to-error-400'
                        : isMedium
                        ? 'bg-gradient-to-t from-warning-500 to-warning-400'
                        : 'bg-gradient-to-t from-success-500 to-success-400'
                    }`}
                    style={{
                      height: `${percentage}%`,
                      minHeight: '4px',
                    }}
                    title={`${item.occupancy}% occupancy`}
                  />
                  <span className="text-xs text-surface-500 mt-1">{item.hour}h</span>
                </div>
              );
            })}
          </div>
        </motion.div>

        {/* Wait Times */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl p-6 shadow-sm border border-surface-100"
        >
          <h3 className="text-xl font-semibold text-surface-900 mb-4">Wait Times by Area</h3>
          <div className="space-y-4">
            {stats?.wait_times_by_area.map((area, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="space-y-2"
              >
                <div className="flex justify-between text-sm">
                  <span className="text-surface-700 font-medium">{area.area}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-surface-500 text-xs">Avg: {area.avg_wait}m</span>
                    <span className={`font-semibold ${
                      area.current_wait > 10
                        ? 'text-error-600'
                        : area.current_wait > 5
                        ? 'text-warning-600'
                        : 'text-success-600'
                    }`}>
                      {area.current_wait}m
                    </span>
                  </div>
                </div>
                <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min((area.current_wait / 15) * 100, 100)}%` }}
                    transition={{ delay: i * 0.1 }}
                    className={`h-full rounded-full ${
                      area.current_wait > 10
                        ? 'bg-error-500'
                        : area.current_wait > 5
                        ? 'bg-warning-500'
                        : 'bg-success-500'
                    }`}
                  />
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Recent Events */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden"
        >
          <div className="px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white">
            <h3 className="text-xl font-semibold text-surface-900">Recent Events</h3>
          </div>
          <div className="divide-y divide-surface-100 max-h-[400px] overflow-y-auto">
            {events.map((event, i) => {
              const severityColor = getSeverityColor(event.severity);
              return (
                <motion.div
                  key={event.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-4 hover:bg-surface-50 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-lg bg-${severityColor}-100 text-xl`}>
                      {getEventIcon(event.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <h4 className="text-sm font-semibold text-surface-900">{event.description}</h4>
                          <p className="text-xs text-surface-500 mt-0.5">{event.details}</p>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-semibold bg-${severityColor}-100 text-${severityColor}-700 whitespace-nowrap`}>
                          {event.severity}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 mt-2 text-xs text-surface-500">
                        <span>📹 {event.camera}</span>
                        <span>🕐 {event.timestamp}</span>
                      </div>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      </div>

      {/* Info Panel */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="bg-gradient-to-r from-primary-50 to-primary-100 rounded-2xl p-6 border border-primary-200"
      >
        <div className="flex items-start gap-4">
          <span className="text-3xl">🤖</span>
          <div className="flex-1">
            <h4 className="font-semibold text-primary-900 mb-2">AI-Powered Video Analytics</h4>
            <p className="text-sm text-primary-700 leading-relaxed">
              Our computer vision system analyzes live camera feeds to provide real-time insights on crowd density,
              wait times, occupancy levels, and safety compliance. The system uses advanced machine learning to detect
              patterns, predict congestion, and alert staff to potential issues before they impact customer experience.
              All processing is done on-device to ensure privacy and data security.
            </p>
          </div>
          <div className="flex gap-2">
            <button className="px-4 py-2 bg-primary-500 text-gray-900 rounded-lg hover:bg-primary-600 transition-colors text-sm font-medium">
              Configure Alerts
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
