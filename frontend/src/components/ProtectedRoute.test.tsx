import { render, screen, act } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { ProtectedRoute } from './ProtectedRoute';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/contexts/AuthContext';

function LocationDisplay() {
  const location = useLocation();
  return <div data-testid="location-display">{location.pathname}</div>;
}

function TestApp() {
  const navigate = useNavigate();
  return (
    <div>
      <LocationDisplay />
      <button onClick={() => navigate('/protected')}>Go to Protected</button>
      <button onClick={() => navigate(-1)}>Go Back</button>
      <Routes>
        <Route path="/public" element={<div>Public Page</div>} />
        <Route path="/login" element={<div>Login Page</div>} />
        <Route
          path="/protected"
          element={
            <ProtectedRoute>
              <div>Protected Content</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </div>
  );
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  test('usuário autenticado consegue visualizar o conteúdo protegido', () => {
    localStorage.setItem('access_token', 'valid_token');

    render(
      <QueryClientProvider client={new QueryClient()}><AuthProvider>
        <MemoryRouter initialEntries={['/protected']}>
          <TestApp />
        </MemoryRouter>
      </AuthProvider></QueryClientProvider>
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
    expect(screen.getByTestId('location-display')).toHaveTextContent('/protected');
  });

  test('usuário não autenticado é redirecionado para /login', () => {
    render(
      <QueryClientProvider client={new QueryClient()}><AuthProvider>
        <MemoryRouter initialEntries={['/protected']}>
          <TestApp />
        </MemoryRouter>
      </AuthProvider></QueryClientProvider>
    );

    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.getByTestId('location-display')).toHaveTextContent('/login');
  });

  test('o redirecionamento substitui a entrada anterior no histórico, conforme replace', () => {
    render(
      <QueryClientProvider client={new QueryClient()}><AuthProvider>
        <MemoryRouter initialEntries={['/public']}>
          <TestApp />
        </MemoryRouter>
      </AuthProvider></QueryClientProvider>
    );

    expect(screen.getByTestId('location-display')).toHaveTextContent('/public');

    act(() => {
      screen.getByRole('button', { name: 'Go to Protected' }).click();
    });

    // Como não está autenticado, é redirecionado para /login substituindo /protected no histórico
    expect(screen.getByTestId('location-display')).toHaveTextContent('/login');

    // Ao ir para trás no histórico, se replace funcionou, deve voltar para /public e não ficar num loop em /protected
    act(() => {
      screen.getByRole('button', { name: 'Go Back' }).click();
    });

    expect(screen.getByTestId('location-display')).toHaveTextContent('/public');
  });
});
