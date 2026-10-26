import axios, { AxiosError, AxiosHeaders } from 'axios';
import { afterEach, expect, it, vi } from 'vitest';
import { api, resetApiSession } from './api';
afterEach(() => { vi.restoreAllMocks(); localStorage.clear(); });
it('refresh antigo não restaura tokens nem apaga a nova sessão depois do logout', async () => {
  localStorage.setItem('access_token', 'old'); localStorage.setItem('refresh_token', 'old-refresh');
  let finish!: (data: unknown) => void;
  const refresh = vi.spyOn(axios, 'post').mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  api.defaults.adapter = async config => { throw new AxiosError('401', 'ERR_BAD_REQUEST', config, undefined, { data: {}, status: 401, statusText: '', headers: new AxiosHeaders(), config }); };
  const request = api.get('/private').catch(error => error);
  await vi.waitFor(() => expect(refresh).toHaveBeenCalledOnce());
  resetApiSession();
  localStorage.setItem('access_token', 'new'); localStorage.setItem('refresh_token', 'new-refresh');
  finish({ data: { access: 'stale', refresh: 'stale-refresh' } });
  await request;
  expect(localStorage.getItem('access_token')).toBe('new');
  expect(localStorage.getItem('refresh_token')).toBe('new-refresh');
});
