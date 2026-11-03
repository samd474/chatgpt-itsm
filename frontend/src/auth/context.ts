import { createContext, useContext } from "react";
import type { User } from "../types";

export type AuthContextValue = {
  user: User | null;
  loading: boolean;
  /** Resolves to the user, or "two_factor" when a code is needed next (see verifyTwoFactor). */
  login: (username: string, password: string) => Promise<User | "two_factor">;
  verifyTwoFactor: (token: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
