import { expect, it } from 'vitest';
import { isLocalPreview, resolveApiUrl } from './visual-preview';

it('enables preview only in its dev mode against a loopback API', () => {
  expect(isLocalPreview(true, 'visual-preview', 'http://127.0.0.1:8000/api')).toBe(true);
  expect(isLocalPreview(true, 'visual-preview', 'https://production.example/api')).toBe(false);
  expect(isLocalPreview(false, 'visual-preview', 'http://127.0.0.1:8000/api')).toBe(false);
  expect(isLocalPreview(true, 'development', 'http://127.0.0.1:8000/api')).toBe(false);
  expect(isLocalPreview(true, 'visual-preview', 'not a URL')).toBe(false);
});

it('recusa iniciar a API da prévia se uma variável de ambiente apontar para produção', () => {
  expect(() => resolveApiUrl('visual-preview', 'https://production.example/api')).toThrow(/API local/);
  expect(() => resolveApiUrl('visual-preview', '')).toThrow(/API local/);
  expect(resolveApiUrl('visual-preview', 'http://127.0.0.1:8000/api')).toBe('http://127.0.0.1:8000/api');
  expect(resolveApiUrl('production', 'https://production.example/api')).toBe('https://production.example/api');
});
