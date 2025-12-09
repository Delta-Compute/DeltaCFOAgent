"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { initializeApp, getApps } from "firebase/app";
import {
  getAuth,
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  User as FirebaseUser,
} from "firebase/auth";

// Firebase config - matches the legacy Flask app (aicfo-473816 project)
const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || "AIzaSyCNRnhRXG_MW4MZJjbw9V5KO1DZrkJD3Cg",
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || "aicfo-473816.firebaseapp.com",
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "aicfo-473816",
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || "aicfo-473816.firebasestorage.app",
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "620026562181",
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || "1:620026562181:web:05e9ca3e4b868585b04bec",
};

// Initialize Firebase (only once)
const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
const firebaseAuth = getAuth(app);

// Types
export interface User {
  id: string;
  email: string;
  display_name: string;
  user_type: string;
  firebase_uid?: string;
}

export interface Tenant {
  id: string;
  company_name: string;
  description: string;
  role: string;
  permissions: Record<string, boolean>;
}

interface AuthContextType {
  user: User | null;
  tenants: Tenant[];
  currentTenant: Tenant | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  switchTenant: (tenantId: string) => Promise<void>;
}

// Context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Provider
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [currentTenant, setCurrentTenant] = useState<Tenant | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Listen for Firebase auth state changes
  useEffect(() => {
    let authResolved = false;
    console.log("[Auth] Setting up onAuthStateChanged listener...");

    const unsubscribe = onAuthStateChanged(firebaseAuth, async (firebaseUser) => {
      authResolved = true;
      console.log("[Auth] onAuthStateChanged fired, user:", firebaseUser?.email || "null");
      try {
        if (firebaseUser) {
          console.log("[Auth] User found, syncing with backend...");
          await syncWithBackend(firebaseUser);
        } else {
          console.log("[Auth] No user, clearing state");
          setUser(null);
          setTenants([]);
          setCurrentTenant(null);
          setIsLoading(false);
        }
      } catch (error) {
        console.error("[Auth] Auth state change error:", error);
        setUser(null);
        setIsLoading(false);
      }
    });

    // Safety timeout - if Firebase doesn't respond in 5 seconds, stop loading
    const timeout = setTimeout(() => {
      if (!authResolved) {
        console.warn("[Auth] Firebase auth timed out - proceeding without auth");
        setIsLoading(false);
      }
    }, 5000);

    return () => {
      unsubscribe();
      clearTimeout(timeout);
    };
  }, []);

  async function syncWithBackend(firebaseUser: FirebaseUser) {
    console.log("[Auth] syncWithBackend starting for:", firebaseUser.email);
    try {
      console.log("[Auth] Getting ID token...");
      const idToken = await firebaseUser.getIdToken();
      console.log("[Auth] Got ID token, calling /api/auth/login...");

      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: idToken }),
        credentials: "include",
      });

      console.log("[Auth] Backend response status:", response.status);

      if (response.ok) {
        const data = await response.json();
        console.log("[Auth] Backend response data:", { success: data.success, hasUser: !!data.user });
        if (data.success) {
          setUser(data.user);
          setTenants(data.tenants || []);
          setCurrentTenant(data.current_tenant || null);
          console.log("[Auth] User set successfully:", data.user?.email);
        } else {
          console.warn("[Auth] User not found in backend:", data.message);
          setUser(null);
        }
      } else {
        console.error("[Auth] Backend sync failed:", response.status);
        setUser(null);
      }
    } catch (error) {
      console.error("[Auth] Backend sync error:", error);
      setUser(null);
    } finally {
      console.log("[Auth] syncWithBackend complete, setting isLoading=false");
      setIsLoading(false);
    }
  }

  async function login(email: string, password: string) {
    setIsLoading(true);
    try {
      await signInWithEmailAndPassword(firebaseAuth, email, password);
      // onAuthStateChanged will handle the rest
    } catch (error) {
      setIsLoading(false);
      throw error;
    }
  }

  async function logout() {
    console.log("[Auth] Logout initiated");
    setIsLoading(true);
    try {
      // Get the current Firebase user to send the token
      const firebaseUser = firebaseAuth.currentUser;
      console.log("[Auth] Firebase user:", firebaseUser?.email);

      if (firebaseUser) {
        const idToken = await firebaseUser.getIdToken();
        console.log("[Auth] Got ID token, calling backend logout...");

        const response = await fetch("/api/auth/logout", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${idToken}`,
            "Content-Type": "application/json",
          },
          credentials: "include",
        });

        console.log("[Auth] Backend logout response:", response.status);
      }

      // Sign out from Firebase regardless of backend response
      console.log("[Auth] Signing out from Firebase...");
      await signOut(firebaseAuth);
      console.log("[Auth] Firebase signout complete");

      setUser(null);
      setTenants([]);
      setCurrentTenant(null);
      console.log("[Auth] State cleared, redirecting to login...");

      // Force redirect to login page
      window.location.href = "/login";
    } catch (error) {
      console.error("[Auth] Logout error:", error);
      // Still try to sign out from Firebase even if something failed
      try {
        await signOut(firebaseAuth);
      } catch (e) {
        console.error("[Auth] Firebase signout also failed:", e);
      }
      setUser(null);
      setTenants([]);
      setCurrentTenant(null);
      // Force redirect even on error
      window.location.href = "/login";
    } finally {
      setIsLoading(false);
    }
  }

  async function refreshUser() {
    const firebaseUser = firebaseAuth.currentUser;
    if (firebaseUser) {
      await syncWithBackend(firebaseUser);
    }
  }

  async function switchTenant(tenantId: string) {
    try {
      const response = await fetch(`/api/auth/switch-tenant/${tenantId}`, {
        method: "POST",
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setCurrentTenant(data.tenant);
        }
      }
    } catch (error) {
      console.error("Switch tenant error:", error);
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        tenants,
        currentTenant,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        refreshUser,
        switchTenant,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// Hook
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
