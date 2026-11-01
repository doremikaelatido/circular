import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, jsonBody, setAccessToken } from "../../lib/api";
import type { User } from "../../types";

interface AuthContextValue {
  user: User | null;
  busy: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, nickname: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

interface AuthPayload {
  access_token: string;
  user: User;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function authenticate(path: string, body: unknown) {
    setBusy(true);
    setError(null);
    try {
      const result = await api<AuthPayload>(path, { method: "POST", body: jsonBody(body) });
      queryClient.clear();
      setAccessToken(result.access_token);
      setUser(result.user);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to sign in");
      throw cause;
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    setAccessToken(null);
    setUser(null);
    queryClient.clear();
  }

  const value = useMemo<AuthContextValue>(() => ({
    user,
    busy,
    error,
    login: (email, password) => authenticate("/auth/login", { email, password }),
    register: (email, password, nickname) => authenticate("/auth/register", { email, password, nickname }),
    logout,
  }), [user, busy, error]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
