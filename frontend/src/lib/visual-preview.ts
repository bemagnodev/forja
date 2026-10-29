export function isLocalPreview(dev: boolean, mode: string, apiUrl: string) {
  if (!dev || mode !== 'visual-preview') return false;
  try {
    const url = new URL(apiUrl);
    return url.protocol === 'http:' && ['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname);
  } catch { return false; }
}

export function resolveApiUrl(mode: string, configuredUrl: string | undefined) {
  if (mode === 'visual-preview' && !isLocalPreview(true, mode, configuredUrl || '')) {
    throw new Error('A prévia visual exige uma API local explícita em VITE_API_URL.');
  }
  return configuredUrl || 'http://127.0.0.1:8000/api';
}

export const visualPreview = isLocalPreview(import.meta.env.DEV, import.meta.env.MODE, import.meta.env.VITE_API_URL || '');
