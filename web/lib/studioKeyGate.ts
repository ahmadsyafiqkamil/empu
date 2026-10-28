export function isStudioKeySubmittable(key: string): boolean {
  return key.trim().length > 0;
}

export function isStudioKeyUnauthorized(error: unknown): boolean {
  return error instanceof Error && error.message.startsWith("401");
}
