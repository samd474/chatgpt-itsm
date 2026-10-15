import { useCallback, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getCsrf, getCurrentUser, loginUser, logoutUser } from "../api/auth";
import type { User } from "../types";
import { AuthContext } from "./context";

// Asks Django who the current user is. There is no client-side token: the
// browser holds an HttpOnly session cookie and the server decides.
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      setUser(await getCurrentUser());
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        await getCsrf();
        const current = await getCurrentUser();
        if (active) setUser(current);
      } catch {
        if (active) setUser(null);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    await loginUser(username, password);
    // Django rotates the CSRF token on login; fetch the fresh one.
    await getCsrf();
    const current = await getCurrentUser();
    setUser(current);
    return current;
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutUser();
    } finally {
      setUser(null);
      queryClient.clear();
      await getCsrf().catch(() => undefined);
    }
  }, [queryClient]);

  const value = useMemo(() => ({ user, loading, login, logout, refreshUser }), [user, loading, login, logout, refreshUser]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
