import axios, { InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import { beforeEach, describe, expect, test, vi } from 'vitest';

describe('Axios API & Interceptors (src/lib/api.ts)', () => {
  let originalLocation: Location;

  beforeEach(() => {
    vi.resetModules();
    localStorage.clear();
    vi.restoreAllMocks();

    originalLocation = window.location;
    delete (window as { location?: unknown }).location;
    window.location = {
      pathname: '/dashboard',
      href: '/dashboard',
    } as unknown as Location;
  });

  afterEach(() => {
    window.location = originalLocation;
  });

  const getApiModule = async () => {
    const mod = await import('./api');
    return mod.api;
  };

  describe('Interceptador de requisição', () => {
    test('1. adiciona Authorization: Bearer <access_token> quando existe token', async () => {
      localStorage.setItem('access_token', 'token_teste_123');
      const api = await getApiModule();

      let capturedConfig: InternalAxiosRequestConfig | undefined;
      api.defaults.adapter = async (config) => {
        capturedConfig = config;
        return {
          data: { success: true },
          status: 200,
          statusText: 'OK',
          headers: {},
          config,
        } as AxiosResponse;
      };

      await api.get('/protected-data');

      expect(capturedConfig?.headers.Authorization).toBe('Bearer token_teste_123');
    });

    test('2. não adiciona o cabeçalho quando não existe token', async () => {
      const api = await getApiModule();

      let capturedConfig: InternalAxiosRequestConfig | undefined;
      api.defaults.adapter = async (config) => {
        capturedConfig = config;
        return {
          data: { success: true },
          status: 200,
          statusText: 'OK',
          headers: {},
          config,
        } as AxiosResponse;
      };

      await api.get('/public-data');

      expect(capturedConfig?.headers.Authorization).toBeUndefined();
    });
  });

  describe('Respostas e silent refresh', () => {
    test('3. uma resposta que não seja 401 não tenta renovar token', async () => {
      localStorage.setItem('refresh_token', 'valid_refresh');
      const api = await getApiModule();
      const axiosPostSpy = vi.spyOn(axios, 'post');

      api.defaults.adapter = async (config) => {
        return {
          data: { success: true },
          status: 200,
          statusText: 'OK',
          headers: {},
          config,
        } as AxiosResponse;
      };

      await api.get('/some-data');

      expect(axiosPostSpy).not.toHaveBeenCalled();
    });

    test('4. 401 em uma requisição comum chama /token/refresh quando existe refresh token', async () => {
      localStorage.setItem('access_token', 'old_access');
      localStorage.setItem('refresh_token', 'valid_refresh');
      const api = await getApiModule();

      const axiosPostSpy = vi.spyOn(axios, 'post').mockResolvedValueOnce({
        data: { access: 'new_access_token' },
      });

      let callCount = 0;
      api.defaults.adapter = async (config) => {
        callCount++;
        if (callCount === 1) {
          throw {
            config,
            response: { status: 401, data: { detail: 'Token expired' } },
          };
        }
        return {
          data: { success: true },
          status: 200,
          statusText: 'OK',
          headers: {},
          config,
        } as AxiosResponse;
      };

      await api.get('/protected');

      expect(axiosPostSpy).toHaveBeenCalledWith(
        expect.stringContaining('/token/refresh'),
        { refresh: 'valid_refresh' }
      );
    });

    test('5. salva o novo access token no localStorage', async () => {
      localStorage.setItem('access_token', 'old_access');
      localStorage.setItem('refresh_token', 'valid_refresh');
      const api = await getApiModule();

      vi.spyOn(axios, 'post').mockResolvedValueOnce({
        data: { access: 'brand_new_access_token' },
      });

      let callCount = 0;
      api.defaults.adapter = async (config) => {
        callCount++;
        if (callCount === 1) {
          throw {
            config,
            response: { status: 401 },
          };
        }
        return {
          data: { success: true },
          status: 200,
          statusText: 'OK',
          headers: {},
          config,
        } as AxiosResponse;
      };

      await api.get('/protected');

      expect(localStorage.getItem('access_token')).toBe('brand_new_access_token');
    });

    test('6. atualiza o refresh token caso o backend também retorne um novo', async () => {
      localStorage.setItem('access_token', 'old_access');
      localStorage.setItem('refresh_token', 'old_refresh');
      const api = await getApiModule();

      vi.spyOn(axios, 'post').mockResolvedValueOnce({
        data: {
          access: 'new_access_token',
          refresh: 'rotated_refresh_token',
        },
      });

      let callCount = 0;
      api.defaults.adapter = async (config) => {
        callCount++;
        if (callCount === 1) {
          throw {
            config,
            response: { status: 401 },
          };
        }
        return {
          data: { success: true },
          status: 200,
          statusText: 'OK',
          headers: {},
          config,
        } as AxiosResponse;
      };

      await api.get('/protected');

      expect(localStorage.getItem('refresh_token')).toBe('rotated_refresh_token');
    });

    test('7. repete a requisição original com o novo access token', async () => {
      localStorage.setItem('access_token', 'old_access');
      localStorage.setItem('refresh_token', 'valid_refresh');
      const api = await getApiModule();

      vi.spyOn(axios, 'post').mockResolvedValueOnce({
        data: { access: 'new_access_token' },
      });

      let retriedConfig: InternalAxiosRequestConfig | undefined;
      let callCount = 0;

      api.defaults.adapter = async (config) => {
        callCount++;
        if (callCount === 1) {
          throw {
            config,
            response: { status: 401 },
          };
        }
        retriedConfig = config;
        return {
          data: { data: 'secret_content' },
          status: 200,
          statusText: 'OK',
          headers: {},
          config,
        } as AxiosResponse;
      };

      const res = await api.get('/protected');

      expect(res.data).toEqual({ data: 'secret_content' });
      expect(retriedConfig?.headers.Authorization).toBe('Bearer new_access_token');
    });

    test('8. não tenta refresh em endpoints contendo /token/', async () => {
      localStorage.setItem('refresh_token', 'valid_refresh');
      const api = await getApiModule();
      const axiosPostSpy = vi.spyOn(axios, 'post');

      api.defaults.adapter = async (config) => {
        throw {
          config,
          response: { status: 401, data: { message: 'Invalid credentials' } },
        };
      };

      await expect(api.post('/token/pair', { u: 'a', p: 'b' })).rejects.toBeDefined();

      expect(axiosPostSpy).not.toHaveBeenCalled();
    });

    test('9. não entra em loop caso a requisição repetida falhe', async () => {
      localStorage.setItem('access_token', 'old_access');
      localStorage.setItem('refresh_token', 'valid_refresh');
      const api = await getApiModule();

      const axiosPostSpy = vi.spyOn(axios, 'post').mockResolvedValueOnce({
        data: { access: 'new_access_token' },
      });

      api.defaults.adapter = async (config) => {
        throw {
          config,
          response: { status: 401 },
        };
      };

      await expect(api.get('/protected')).rejects.toBeDefined();

      expect(axiosPostSpy).toHaveBeenCalledTimes(1);
    });

    test('10. falha do refresh remove os dois tokens', async () => {
      localStorage.setItem('access_token', 'old_access');
      localStorage.setItem('refresh_token', 'invalid_refresh');
      const api = await getApiModule();

      vi.spyOn(axios, 'post').mockRejectedValueOnce(new Error('Refresh failed'));

      api.defaults.adapter = async (config) => {
        throw {
          config,
          response: { status: 401 },
        };
      };

      await expect(api.get('/protected')).rejects.toThrow('Refresh failed');

      expect(localStorage.getItem('access_token')).toBeNull();
      expect(localStorage.getItem('refresh_token')).toBeNull();
    });

    test('11. falha do refresh redireciona para /login', async () => {
      localStorage.setItem('access_token', 'old_access');
      localStorage.setItem('refresh_token', 'invalid_refresh');
      const api = await getApiModule();

      vi.spyOn(axios, 'post').mockRejectedValueOnce(new Error('Refresh failed'));

      api.defaults.adapter = async (config) => {
        throw {
          config,
          response: { status: 401 },
        };
      };

      await expect(api.get('/protected')).rejects.toBeDefined();

      expect(window.location.href).toBe('/login');
    });

    test('12. ausência de refresh token remove a autenticação e não chama o endpoint de refresh', async () => {
      localStorage.setItem('access_token', 'old_access');
      const api = await getApiModule();
      const axiosPostSpy = vi.spyOn(axios, 'post');

      api.defaults.adapter = async (config) => {
        throw {
          config,
          response: { status: 401 },
        };
      };

      await expect(api.get('/protected')).rejects.toBeDefined();

      expect(axiosPostSpy).not.toHaveBeenCalled();
      expect(localStorage.getItem('access_token')).toBeNull();
      expect(window.location.href).toBe('/login');
    });

    test('13. duas ou mais requisições simultâneas com 401 devem provocar somente uma chamada de refresh', async () => {
      localStorage.setItem('access_token', 'old_access');
      localStorage.setItem('refresh_token', 'valid_refresh');
      const api = await getApiModule();

      let resolveRefresh!: (val: AxiosResponse<{ access: string }>) => void;
      const refreshPromise = new Promise<AxiosResponse<{ access: string }>>((resolve) => {
        resolveRefresh = resolve;
      });

      const axiosPostSpy = vi.spyOn(axios, 'post').mockReturnValueOnce(refreshPromise);

      api.defaults.adapter = async (config) => {
        if (!config._retry) {
          throw {
            config,
            response: { status: 401 },
          };
        }
        return {
          data: { url: config.url },
          status: 200,
          statusText: 'OK',
          headers: {},
          config,
        } as AxiosResponse;
      };

      const p1 = api.get('/req1');
      const p2 = api.get('/req2');

      resolveRefresh({
        data: { access: 'shared_new_access' },
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });

      await Promise.all([p1, p2]);

      expect(axiosPostSpy).toHaveBeenCalledTimes(1);
    });

    test('14. as requisições enfileiradas devem ser repetidas com o mesmo novo access token', async () => {
      localStorage.setItem('access_token', 'old_access');
      localStorage.setItem('refresh_token', 'valid_refresh');
      const api = await getApiModule();

      let resolveRefresh!: (val: AxiosResponse<{ access: string }>) => void;
      const refreshPromise = new Promise<AxiosResponse<{ access: string }>>((resolve) => {
        resolveRefresh = resolve;
      });

      vi.spyOn(axios, 'post').mockReturnValueOnce(refreshPromise);

      const retryConfigs: InternalAxiosRequestConfig[] = [];

      api.defaults.adapter = async (config) => {
        if (!config._retry) {
          throw {
            config,
            response: { status: 401 },
          };
        }
        retryConfigs.push(config);
        return {
          data: { url: config.url },
          status: 200,
          statusText: 'OK',
          headers: {},
          config,
        } as AxiosResponse;
      };

      const p1 = api.get('/req1');
      const p2 = api.get('/req2');

      resolveRefresh({
        data: { access: 'shared_new_access' },
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });

      const [res1, res2] = await Promise.all([p1, p2]);

      expect(res1.data).toEqual({ url: '/req1' });
      expect(res2.data).toEqual({ url: '/req2' });

      expect(retryConfigs).toHaveLength(2);
      expect(retryConfigs[0].headers.Authorization).toBe('Bearer shared_new_access');
      expect(retryConfigs[1].headers.Authorization).toBe('Bearer shared_new_access');
    });

    test('15. se o refresh falhar, todas as requisições enfileiradas devem ser rejeitadas', async () => {
      localStorage.setItem('access_token', 'old_access');
      localStorage.setItem('refresh_token', 'invalid_refresh');
      const api = await getApiModule();

      let rejectRefresh!: (err: unknown) => void;
      // Promise tipada como AxiosResponse — será rejeitada, nunca resolvida.
      const refreshPromise = new Promise<AxiosResponse>((_, reject) => {
        rejectRefresh = reject;
      });

      vi.spyOn(axios, 'post').mockReturnValueOnce(refreshPromise);

      api.defaults.adapter = async (config) => {
        if (!config._retry) {
          throw {
            config,
            response: { status: 401 },
          };
        }
        return {
          data: { success: true },
          status: 200,
          statusText: 'OK',
          headers: {},
          config,
        } as AxiosResponse;
      };

      const p1 = api.get('/req1');
      const p2 = api.get('/req2');

      rejectRefresh(new Error('Refresh failed'));

      await expect(p1).rejects.toThrow('Refresh failed');
      await expect(p2).rejects.toThrow('Refresh failed');
    });
  });
});
