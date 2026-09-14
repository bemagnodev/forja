import { render, screen, act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { AuthProvider, useAuth } from './AuthContext';

function TestConsumer() {
  const { isAuthenticated, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="auth-status">
        {isAuthenticated ? 'authenticated' : 'unauthenticated'}
      </span>
      <button onClick={() => login('access_123', 'refresh_456')}>Login</button>
      <button onClick={() => logout()}>Logout</button>
    </div>
  );
}

describe('AuthContext', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  test('inicia não autenticado quando não existe access_token', () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId('auth-status')).toHaveTextContent('unauthenticated');
  });

  test('inicia autenticado quando o access_token já existe', () => {
    localStorage.setItem('access_token', 'existing_access');

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');
  });

  test('login(access, refresh) salva os dois tokens no localStorage', () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    act(() => {
      screen.getByRole('button', { name: 'Login' }).click();
    });

    expect(localStorage.getItem('access_token')).toBe('access_123');
    expect(localStorage.getItem('refresh_token')).toBe('refresh_456');
  });

  test('login atualiza isAuthenticated para true', () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId('auth-status')).toHaveTextContent('unauthenticated');

    act(() => {
      screen.getByRole('button', { name: 'Login' }).click();
    });

    expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');
  });

  test('logout() remove os dois tokens do localStorage', () => {
    localStorage.setItem('access_token', 'existing_access');
    localStorage.setItem('refresh_token', 'existing_refresh');

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    act(() => {
      screen.getByRole('button', { name: 'Logout' }).click();
    });

    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
  });

  test('logout atualiza isAuthenticated para false', () => {
    localStorage.setItem('access_token', 'existing_access');

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');

    act(() => {
      screen.getByRole('button', { name: 'Logout' }).click();
    });

    expect(screen.getByTestId('auth-status')).toHaveTextContent('unauthenticated');
  });

  test('useAuth fora de AuthProvider lança o erro esperado', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => renderHook(() => useAuth())).toThrow(
      'useAuth must be used within an AuthProvider'
    );

    consoleSpy.mockRestore();
  });
});
