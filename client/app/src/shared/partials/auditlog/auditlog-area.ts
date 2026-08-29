/**
 * The audit log is served on the area of the role that reads it: the
 * administrator reaches it under /api/admin, the auditor under /api/auditor.
 * The two areas export the same implementation, so what changes between them
 * is the path alone. A role that is served no audit log yields no area.
 */
export function auditLogArea(role: string): string {
  return role === "admin" || role === "auditor" ? role : "";
}
