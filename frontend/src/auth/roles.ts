import type { User } from "../types";

export function hasRole(user: User | null, ...roles: string[]): boolean {
  if (!user) return false;
  if (user.is_superuser && roles.includes("Administrator")) return true;
  const groups = new Set(user.groups.map((g) => g.toLowerCase()));
  return roles.some((role) => groups.has(role.toLowerCase()));
}

export const isStaff = (user: User | null) => hasRole(user, "Technician", "Manager", "Administrator");

export function homePath(user: User): string {
  if (hasRole(user, "Administrator")) return "/admin/config";
  if (hasRole(user, "Technician", "Manager")) return "/tech/queue";
  if (hasRole(user, "Auditor")) return "/audit";
  return "/portal";
}
