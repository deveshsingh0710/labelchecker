// ==============================================================================
// Frontend Configuration & Production Asset Resolution
// ==============================================================================

/**
 * Base URL for the FastAPI backend.
 * In development, defaults to empty string '' (relying on Vite reverse proxy).
 * In production (e.g. deployed on Vercel), set VITE_API_BASE_URL to your backend URL:
 * e.g. https://labelchecker-api.onrender.com
 */
export const API_BASE_URL: string = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

/**
 * Normalizes backend image and report asset URLs.
 * Ensures relative paths like '/static/uploads/...' or '/api/verifications/.../pdf'
 * resolve to the full backend origin when frontend and backend are hosted on separate domains.
 */
export const getAssetUrl = (path?: string | null): string => {
  if (!path) return '';
  if (
    path.startsWith('http://') ||
    path.startsWith('https://') ||
    path.startsWith('data:') ||
    path.startsWith('blob:')
  ) {
    return path;
  }

  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return API_BASE_URL ? `${API_BASE_URL}${cleanPath}` : cleanPath;
};
