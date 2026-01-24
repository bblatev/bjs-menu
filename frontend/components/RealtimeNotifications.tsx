"use client";

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNotificationWebSocket, WebSocketMessage, EventType } from '@/hooks/useWebSocket';

interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: Date;
  actionUrl?: string;
}

interface RealtimeNotificationsProps {
  venueId: number;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
  maxNotifications?: number;
  autoHideDuration?: number;
}

const getNotificationFromEvent = (wsMessage: WebSocketMessage): Notification | null => {
  const baseNotification = {
    id: `${wsMessage.event}-${Date.now()}-${Math.random()}`,
    timestamp: new Date(wsMessage.timestamp),
  };

  switch (wsMessage.event) {
    case EventType.RFID_ALERT:
      return {
        ...baseNotification,
        type: wsMessage.data.priority === 'high' ? 'warning' : 'info',
        title: 'RFID Alert',
        message: wsMessage.data.message as string || 'RFID tag alert triggered',
      };

    case EventType.KEG_LOW:
      return {
        ...baseNotification,
        type: 'warning',
        title: 'Keg Running Low',
        message: `${wsMessage.data.product_name} is at ${wsMessage.data.fill_percentage}%`,
        actionUrl: '/bar/kegs',
      };

    case EventType.KEG_EMPTY:
      return {
        ...baseNotification,
        type: 'error',
        title: 'Keg Empty!',
        message: `${wsMessage.data.product_name} on tap ${wsMessage.data.tap_number} is empty`,
        actionUrl: '/bar/kegs',
      };

    case EventType.TANK_LOW:
      return {
        ...baseNotification,
        type: 'warning',
        title: 'Tank Level Low',
        message: `${wsMessage.data.tank_name} is at ${wsMessage.data.fill_percentage}%`,
        actionUrl: '/stock/tanks',
      };

    case EventType.LOW_STOCK:
      return {
        ...baseNotification,
        type: 'warning',
        title: 'Low Stock Alert',
        message: `${wsMessage.data.item_name} is running low (${wsMessage.data.quantity} remaining)`,
        actionUrl: '/stock',
      };

    case EventType.OUT_OF_STOCK:
      return {
        ...baseNotification,
        type: 'error',
        title: 'Out of Stock!',
        message: `${wsMessage.data.item_name} is out of stock`,
        actionUrl: '/stock',
      };

    case EventType.TEMPERATURE_ALERT:
      return {
        ...baseNotification,
        type: 'error',
        title: 'Temperature Alert!',
        message: `${wsMessage.data.location}: ${wsMessage.data.temperature} (threshold: ${wsMessage.data.threshold})`,
      };

    case EventType.NEW_ORDER:
      return {
        ...baseNotification,
        type: 'info',
        title: 'New Order',
        message: `Table ${wsMessage.data.table_number} - ${(wsMessage.data.items as Array<Record<string, unknown>>)?.length || 0} items`,
        actionUrl: '/kitchen',
      };

    case EventType.ORDER_READY:
      return {
        ...baseNotification,
        type: 'success',
        title: 'Order Ready',
        message: `Order #${wsMessage.data.order_id} is ready for pickup`,
      };

    case EventType.NOTIFICATION:
      return {
        ...baseNotification,
        type: wsMessage.data.priority === 'critical' ? 'error' :
              wsMessage.data.priority === 'high' ? 'warning' : 'info',
        title: wsMessage.data.title as string || 'Notification',
        message: wsMessage.data.message as string || '',
        actionUrl: wsMessage.data.action_url as string,
      };

    default:
      return null;
  }
};

const getPositionClasses = (position: string) => {
  switch (position) {
    case 'top-left':
      return 'top-4 left-4';
    case 'bottom-right':
      return 'bottom-4 right-4';
    case 'bottom-left':
      return 'bottom-4 left-4';
    default:
      return 'top-4 right-4';
  }
};

const getTypeStyles = (type: string) => {
  switch (type) {
    case 'success':
      return {
        bg: 'bg-green-500',
        border: 'border-green-600',
        icon: (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        ),
      };
    case 'warning':
      return {
        bg: 'bg-yellow-500',
        border: 'border-yellow-600',
        icon: (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        ),
      };
    case 'error':
      return {
        bg: 'bg-red-500',
        border: 'border-red-600',
        icon: (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
        ),
      };
    default:
      return {
        bg: 'bg-blue-500',
        border: 'border-blue-600',
        icon: (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
        ),
      };
  }
};

export function RealtimeNotifications({
  venueId,
  position = 'top-right',
  maxNotifications = 5,
  autoHideDuration = 5000,
}: RealtimeNotificationsProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const { isConnected, lastMessage } = useNotificationWebSocket(venueId);

  // Process incoming WebSocket messages
  useEffect(() => {
    if (lastMessage) {
      const notification = getNotificationFromEvent(lastMessage);
      if (notification) {
        setNotifications((prev) => {
          const updated = [notification, ...prev].slice(0, maxNotifications);
          return updated;
        });
      }
    }
  }, [lastMessage, maxNotifications]);

  // Auto-hide notifications
  useEffect(() => {
    if (notifications.length > 0 && autoHideDuration > 0) {
      const timer = setTimeout(() => {
        setNotifications((prev) => prev.slice(0, -1));
      }, autoHideDuration);
      return () => clearTimeout(timer);
    }
  }, [notifications, autoHideDuration]);

  const removeNotification = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  const handleActionClick = (notification: Notification) => {
    if (notification.actionUrl) {
      window.location.href = notification.actionUrl;
    }
    removeNotification(notification.id);
  };

  return (
    <div className={`fixed ${getPositionClasses(position)} z-50 flex flex-col gap-2 pointer-events-none`}>
      {/* Connection status indicator */}
      <div className="pointer-events-auto">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className={`px-3 py-1 rounded-full text-xs font-medium text-white ${
            isConnected ? 'bg-green-500' : 'bg-red-500'
          }`}
        >
          {isConnected ? 'Live' : 'Reconnecting...'}
        </motion.div>
      </div>

      {/* Notifications */}
      <AnimatePresence mode="popLayout">
        {notifications.map((notification) => {
          const styles = getTypeStyles(notification.type);
          return (
            <motion.div
              key={notification.id}
              initial={{ opacity: 0, x: position.includes('right') ? 100 : -100, scale: 0.9 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: position.includes('right') ? 100 : -100, scale: 0.9 }}
              transition={{ type: 'spring', damping: 20, stiffness: 300 }}
              className={`pointer-events-auto max-w-sm w-80 ${styles.bg} rounded-lg shadow-lg border ${styles.border} overflow-hidden`}
            >
              <div className="p-4">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 text-white">
                    {styles.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-white truncate">
                      {notification.title}
                    </p>
                    <p className="text-sm text-white/90 mt-1">
                      {notification.message}
                    </p>
                    <p className="text-xs text-white/70 mt-2">
                      {notification.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                  <button
                    onClick={() => removeNotification(notification.id)}
                    className="flex-shrink-0 text-white/80 hover:text-white transition-colors"
                  >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </button>
                </div>
                {notification.actionUrl && (
                  <button
                    onClick={() => handleActionClick(notification)}
                    className="mt-3 w-full py-2 bg-white/20 hover:bg-white/30 rounded text-white text-sm font-medium transition-colors"
                  >
                    View Details
                  </button>
                )}
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}

export default RealtimeNotifications;
