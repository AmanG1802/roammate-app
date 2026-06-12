export function clearSession(): void {
  if (typeof window !== 'undefined') localStorage.removeItem('user');
}
