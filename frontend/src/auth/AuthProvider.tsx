import { useCallback, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getCsrf, getCurrentUser, loginUser, logoutUser, verifyTwoFactor as verifyCode } from "../api/auth";
import { SESSION_UNVERIFIED_EVENT } from "../api/client";
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

  const finishLogin = useCallback(async () => {
    // Django rotates the CSRF token on login; fetch the fresh one.
    await getCsrf();
    const current = await getCurrentUser();
    setUser(current);
    return current;
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const { two_factor_required } = await loginUser(username, password);
    return two_factor_required ? "two_factor" as const : finishLogin();
  }, [finishLogin]);

  const verifyTwoFactor = useCallback(async (token: string) => {
    await verifyCode(token);
    return finishLogin();
  }, [finishLogin]);

  // A session that never entered a 2FA code (e.g. 2FA was turned on in another browser) can't use
  // the API: drop to the login page so the user signs in again with a code.
  useEffect(() => {
    const onUnverified = () => { setUser(null); queryClient.clear(); };
    window.addEventListener(SESSION_UNVERIFIED_EVENT, onUnverified);
    return () => window.removeEventListener(SESSION_UNVERIFIED_EVENT, onUnverified);
  }, [queryClient]);

  const logout = useCallback(async () => {
    try {
      await logoutUser();
    } finally {
      setUser(null);
      queryClient.clear();
      await getCsrf().catch(() => undefined);
    }
  }, [queryClient]);

  const value = useMemo(() => ({ user, loading, login, verifyTwoFactor, logout, refreshUser }),
    [user, loading, login, verifyTwoFactor, logout, refreshUser]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
