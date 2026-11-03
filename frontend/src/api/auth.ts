import { api } from "./client";
import type { User } from "../types";

export async function getCsrf(): Promise<void> {
  await api.get("/auth/csrf/");
}

export async function getCurrentUser(): Promise<User> {
  const response = await api.get<User>("/auth/me/");
  return response.data;
}

/** Password step. When `two_factor_required` is true the session isn't signed in until verifyTwoFactor(). */
export async function loginUser(username: string, password: string): Promise<{ two_factor_required: boolean }> {
  await getCsrf();
  return (await api.post<{ two_factor_required: boolean }>("/auth/login/", { username, password })).data;
}

export async function verifyTwoFactor(token: string): Promise<void> {
  await api.post("/auth/2fa/verify/", { token });
}

export async function logoutUser(): Promise<void> {
  await api.post("/auth/logout/");
}

export type TwoFactorStatus = { enabled: boolean; required_by_role: boolean; recovery_codes_left: number };
export type TwoFactorSetup = { otpauth_url: string; secret: string; qr_svg: string };

export async function getTwoFactorStatus(): Promise<TwoFactorStatus> {
  return (await api.get<TwoFactorStatus>("/auth/2fa/")).data;
}

export async function startTwoFactorSetup(): Promise<TwoFactorSetup> {
  return (await api.post<TwoFactorSetup>("/auth/2fa/setup/")).data;
}

/** Returns the recovery codes, which are only ever shown once. */
export async function confirmTwoFactor(token: string): Promise<string[]> {
  return (await api.post<{ recovery_codes: string[] }>("/auth/2fa/confirm/", { token })).data.recovery_codes;
}

export async function replaceRecoveryCodes(token: string): Promise<string[]> {
  return (await api.post<{ recovery_codes: string[] }>("/auth/2fa/recovery-codes/", { token })).data.recovery_codes;
}

export async function disableTwoFactor(token: string): Promise<void> {
  await api.post("/auth/2fa/disable/", { token });
}
