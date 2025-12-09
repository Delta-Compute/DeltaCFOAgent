'use client';

import { useEffect, useRef } from 'react';
import { usePathname } from 'next/navigation';
import { useAnalytics } from '@/context/analytics-context';

export function PageTracker() {
  const pathname = usePathname();
  const { trackPageView } = useAnalytics();
  const previousPathRef = useRef<string | null>(null);

  useEffect(() => {
    // Only track if the path has changed
    if (pathname && pathname !== previousPathRef.current) {
      // Get page title from document or derive from path
      const pageTitle = typeof document !== 'undefined' ? document.title : undefined;

      trackPageView(pathname, pageTitle);
      previousPathRef.current = pathname;
    }
  }, [pathname, trackPageView]);

  return null;
}
