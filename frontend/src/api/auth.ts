import { api } from "./client";
import type { User } from "../types";

export async function getCsrf(): Promise<void> {
  await api.get("/auth/csrf/");
}

export async function getCurrentUser(): Promise<User> {
  const response = await api.get<User>("/auth/me/");
  return response.data;
}

export async function loginUser(username: string, password: string): Promise<void> {
  await getCsrf();
  await api.post("/auth/login/", { username, password });
}

export async function logoutUser(): Promise<void> {
  await api.post("/auth/logout/");
}
