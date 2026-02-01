"use client";

import { useEffect, useRef, useState, useCallback } from 'react';

// WebSocket event types
export enum EventType {
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  PING = 'ping',
  PONG = 'pong',

  // Hardware events
  RFID_SCAN = 'rfid_scan',
  RFID_MOVEMENT = 'rfid_movement',
  RFID_ALERT = 'rfid_alert',
  KEG_UPDATE = 'keg_update',
  KEG_LOW = 'keg_low',
  KEG_EMPTY = 'keg_empty',
  TANK_UPDATE = 'tank_update',
  TANK_LOW = 'tank_low',
  SCALE_READING = 'scale_reading',
  FLOW_READING = 'flow_reading',
  TEMPERATURE_ALERT = 'temperature_alert',

  // Kitchen events
  NEW_ORDER = 'new_order',
  ORDER_UPDATE = 'order_update',
  ORDER_READY = 'order_ready',
  TICKET_BUMP = 'ticket_bump',

  // Stock events
  LOW_STOCK = 'low_stock',
  OUT_OF_STOCK = 'out_of_stock',
  STOCK_RECEIVED = 'stock_received',

  // General
  ALERT = 'alert',
  NOTIFICATION = 'notification',
}

export interface WebSocketMessage {
  event: string;
  data: Record<string, unknown>;
  timestamp: string;
  venue_id: number | null;
}

export interface UseWebSocketOptions {
  venueId: number;
  channels?: string[];
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null;
  messages: WebSocketMessage[];
  send: (event: string, data: Record<string, unknown>) => void;
  subscribe: (channels: string[]) => void;
  unsubscribe: (channels: string[]) => void;
  connect: () => void;
  disconnect: () => void;
}

export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  const {
    venueId,
    channels = ['general'],
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    autoReconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);

  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Remove protocol and any /api/v1 suffix from the URL
    const host = process.env.NEXT_PUBLIC_API_URL
      ?.replace(/^https?:\/\//, '')
      ?.replace(/\/api\/v1\/?$/, '') || 'localhost:8000';
    const channelParam = channels.join(',');
    return `${protocol}//${host}/api/v1/ws/venue/${venueId}?channels=${channelParam}`;
  }, [venueId, channels]);

  const startPingInterval = useCallback(() => {
    pingIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          event: 'ping',
          timestamp: new Date().toISOString(),
        }));
      }
    }, 30000); // Ping every 30 seconds
  }, []);

  const stopPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const url = getWebSocketUrl();
    wsRef.current = new WebSocket(url);

    wsRef.current.onopen = () => {
      setIsConnected(true);
      reconnectAttemptsRef.current = 0;
      startPingInterval();
      onConnect?.();
    };

    wsRef.current.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        setLastMessage(message);
        setMessages((prev) => [...prev.slice(-99), message]); // Keep last 100 messages
        onMessage?.(message);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    wsRef.current.onclose = () => {
      setIsConnected(false);
      stopPingInterval();
      onDisconnect?.();

      // Auto reconnect
      if (autoReconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
        reconnectAttemptsRef.current += 1;
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, reconnectInterval * reconnectAttemptsRef.current);
      }
    };

    wsRef.current.onerror = (error) => {
      onError?.(error);
    };
  }, [
    getWebSocketUrl,
    onConnect,
    onDisconnect,
    onMessage,
    onError,
    autoReconnect,
    reconnectInterval,
    maxReconnectAttempts,
    startPingInterval,
    stopPingInterval,
  ]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    stopPingInterval();
    reconnectAttemptsRef.current = maxReconnectAttempts; // Prevent auto-reconnect
    wsRef.current?.close();
    wsRef.current = null;
    setIsConnected(false);
  }, [maxReconnectAttempts, stopPingInterval]);

  const send = useCallback((event: string, data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ event, ...data }));
    }
  }, []);

  const subscribe = useCallback((newChannels: string[]) => {
    send('subscribe', { channels: newChannels });
  }, [send]);

  const unsubscribe = useCallback((removeChannels: string[]) => {
    send('unsubscribe', { channels: removeChannels });
  }, [send]);

  // Connect on mount
  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [venueId]); // Only reconnect when venueId changes

  return {
    isConnected,
    lastMessage,
    messages,
    send,
    subscribe,
    unsubscribe,
    connect,
    disconnect,
  };
}

// Specialized hooks for specific use cases
export function useKitchenWebSocket(venueId: number, station?: string) {
  return useWebSocket({
    venueId,
    channels: station ? ['kitchen', `station:${station}`] : ['kitchen'],
  });
}

export function useHardwareWebSocket(venueId: number, deviceTypes?: string[]) {
  return useWebSocket({
    venueId,
    channels: deviceTypes
      ? ['hardware', 'inventory', ...deviceTypes.map(dt => `device:${dt}`)]
      : ['hardware', 'inventory'],
  });
}

export function useNotificationWebSocket(venueId: number) {
  return useWebSocket({
    venueId,
    channels: ['general', 'notifications'],
  });
}
