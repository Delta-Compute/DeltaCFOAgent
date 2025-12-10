'use client';

import { createContext, useContext, useCallback, useRef, useEffect, ReactNode } from 'react';
import { useAuth } from './auth-context';
import { analytics, AnalyticsEvent } from '@/lib/api';

interface AnalyticsContextType {
  trackPageView: (pagePath: string, pageTitle?: string, metadata?: Record<string, unknown>) => void;
  trackFeature: (featureName: string, metadata?: Record<string, unknown>) => void;
  trackError: (errorType: string, errorMessage: string, stackTrace?: string, metadata?: Record<string, unknown>) => void;
}

const AnalyticsContext = createContext<AnalyticsContextType | undefined>(undefined);

const BATCH_SIZE = 10;
const FLUSH_INTERVAL_MS = 30000; // 30 seconds

export function AnalyticsProvider({ children }: { children: ReactNode }) {
  const { user, currentTenant } = useAuth();
  const eventQueue = useRef<AnalyticsEvent[]>([]);
  const flushTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Flush events to the backend
  const flushEvents = useCallback(async () => {
    if (eventQueue.current.length === 0) return;

    const eventsToSend = [...eventQueue.current];
    eventQueue.current = [];

    try {
      await analytics.trackBatch(eventsToSend);
    } catch (error) {
      // On error, put events back in queue for retry (but limit queue size)
      console.error('Failed to send analytics events:', error);
      eventQueue.current = [...eventsToSend, ...eventQueue.current].slice(0, 100);
    }
  }, []);

  // Schedule a flush after the interval
  const scheduleFlush = useCallback(() => {
    if (flushTimeoutRef.current) {
      clearTimeout(flushTimeoutRef.current);
    }
    flushTimeoutRef.current = setTimeout(() => {
      flushEvents();
    }, FLUSH_INTERVAL_MS);
  }, [flushEvents]);

  // Add an event to the queue
  const queueEvent = useCallback(
    (event: Omit<AnalyticsEvent, 'user_id' | 'tenant_id' | 'timestamp'>) => {
      const fullEvent: AnalyticsEvent = {
        ...event,
        user_id: user?.id || undefined,
        tenant_id: currentTenant?.id || undefined,
        timestamp: new Date().toISOString(),
      };

      eventQueue.current.push(fullEvent);

      // Flush immediately if batch size reached
      if (eventQueue.current.length >= BATCH_SIZE) {
        flushEvents();
      } else {
        scheduleFlush();
      }
    },
    [user?.id, currentTenant?.id, flushEvents, scheduleFlush]
  );

  // Track page view
  const trackPageView = useCallback(
    (pagePath: string, pageTitle?: string, metadata?: Record<string, unknown>) => {
      queueEvent({
        event_type: 'page_view',
        page_path: pagePath,
        page_title: pageTitle,
        metadata,
      });
    },
    [queueEvent]
  );

  // Track feature usage
  const trackFeature = useCallback(
    (featureName: string, metadata?: Record<string, unknown>) => {
      queueEvent({
        event_type: 'feature',
        feature_name: featureName,
        metadata,
      });
    },
    [queueEvent]
  );

  // Track error
  const trackError = useCallback(
    (errorType: string, errorMessage: string, stackTrace?: string, metadata?: Record<string, unknown>) => {
      queueEvent({
        event_type: 'error',
        error_type: errorType,
        error_message: errorMessage,
        stack_trace: stackTrace,
        metadata,
      });
    },
    [queueEvent]
  );

  // Flush on unmount or page unload
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (eventQueue.current.length > 0) {
        // Use sendBeacon for reliable delivery on page unload
        const events = eventQueue.current;
        const blob = new Blob([JSON.stringify({ events })], { type: 'application/json' });
        navigator.sendBeacon('/api/analytics/track', blob);
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      if (flushTimeoutRef.current) {
        clearTimeout(flushTimeoutRef.current);
      }
      // Final flush on unmount
      flushEvents();
    };
  }, [flushEvents]);

  return (
    <AnalyticsContext.Provider
      value={{
        trackPageView,
        trackFeature,
        trackError,
      }}
    >
      {children}
    </AnalyticsContext.Provider>
  );
}

export function useAnalytics(): AnalyticsContextType {
  const context = useContext(AnalyticsContext);
  if (!context) {
    throw new Error('useAnalytics must be used within an AnalyticsProvider');
  }
  return context;
}
