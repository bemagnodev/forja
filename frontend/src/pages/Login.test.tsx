import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { Login } from './Login';
import { api } from '@/lib/api';
import { AuthProvider } from '@/contexts/AuthContext';
import { ToastProvider } from '@/components/ui/toast';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Login Page', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  const renderLogin = () => {
    return render(
      <AuthProvider>
        <ToastProvider>
          <MemoryRouter>
            <Login />
          </MemoryRouter>
        </ToastProvider>
      </AuthProvider>
    );
  };

  test('renderização dos campos de usuário, senha e botão', () => {
    renderLogin();

    expect(screen.getByLabelText(/^usuário$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^senha$/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /entrar/i })).toBeInTheDocument();
  });

  test('envio das credenciais corretas para POST /token/pair', async () => {
    const user = userEvent.setup();
    const postSpy = vi.spyOn(api, 'post').mockResolvedValueOnce({
      data: { access: 'access_token_123', refresh: 'refresh_token_456' },
    });

    renderLogin();

    await user.type(screen.getByLabelText(/^usuário$/i), 'membro1');
    await user.type(screen.getByLabelText(/^senha$/i), 'senha123');
    await user.click(screen.getByRole('button', { name: /entrar/i }));

    expect(postSpy).toHaveBeenCalledWith('/token/pair', {
      username: 'membro1',
      password: 'senha123',
    });
  });

  test('uso de access e refresh retornados pela API na função login', async () => {
    const user = userEvent.setup();
    vi.spyOn(api, 'post').mockResolvedValueOnce({
      data: { access: 'access_token_123', refresh: 'refresh_token_456' },
    });

    renderLogin();

    await user.type(screen.getByLabelText(/^usuário$/i), 'membro1');
    await user.type(screen.getByLabelText(/^senha$/i), 'senha123');
    await user.click(screen.getByRole('button', { name: /entrar/i }));

    await waitFor(() => {
      expect(localStorage.getItem('access_token')).toBe('access_token_123');
      expect(localStorage.getItem('refresh_token')).toBe('refresh_token_456');
    });
  });

  test('navegação para /dashboard após sucesso', async () => {
    const user = userEvent.setup();
    vi.spyOn(api, 'post').mockResolvedValueOnce({
      data: { access: 'access_123', refresh: 'refresh_456' },
    });

    renderLogin();

    await user.type(screen.getByLabelText(/^usuário$/i), 'membro1');
    await user.type(screen.getByLabelText(/^senha$/i), 'senha123');
    await user.click(screen.getByRole('button', { name: /entrar/i }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });
  });

  test('apresentação do toast de erro em credenciais inválidas', async () => {
    const user = userEvent.setup();
    vi.spyOn(api, 'post').mockRejectedValueOnce(new Error('Unauthorized'));

    renderLogin();

    await user.type(screen.getByLabelText(/^usuário$/i), 'errado');
    await user.type(screen.getByLabelText(/^senha$/i), 'errado');
    await user.click(screen.getByRole('button', { name: /entrar/i }));

    expect(await screen.findByText('Acesso Negado')).toBeInTheDocument();
    expect(
      screen.getByText('Credenciais inválidas. As portas da Forja permanecem fechadas.')
    ).toBeInTheDocument();
  });

  test('o botão exibe estado de carregamento durante a requisição', async () => {
    const user = userEvent.setup();
    let resolveApiPromise!: (value: unknown) => void;
    const apiPromise = new Promise((resolve) => {
      resolveApiPromise = resolve;
    });

    vi.spyOn(api, 'post').mockReturnValueOnce(apiPromise as ReturnType<typeof api.post>);

    renderLogin();

    await user.type(screen.getByLabelText(/^usuário$/i), 'membro1');
    await user.type(screen.getByLabelText(/^senha$/i), 'senha123');
    await user.click(screen.getByRole('button', { name: /entrar/i }));

    const submitButton = screen.getByRole('button', { name: /acessando\.\.\./i });
    expect(submitButton).toBeDisabled();

    // Resolve API request
    resolveApiPromise({ data: { access: 'acc', refresh: 'ref' } });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /entrar/i })).toBeEnabled();
    });
  });

  test('o estado de carregamento termina depois de falha', async () => {
    const user = userEvent.setup();
    let rejectApiPromise!: (reason: unknown) => void;
    const apiPromise = new Promise((_, reject) => {
      rejectApiPromise = reject;
    });

    vi.spyOn(api, 'post').mockReturnValueOnce(apiPromise as ReturnType<typeof api.post>);

    renderLogin();

    await user.type(screen.getByLabelText(/^usuário$/i), 'membro1');
    await user.type(screen.getByLabelText(/^senha$/i), 'senha123');
    await user.click(screen.getByRole('button', { name: /entrar/i }));

    expect(screen.getByRole('button', { name: /acessando\.\.\./i })).toBeDisabled();

    rejectApiPromise(new Error('Fail'));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /entrar/i })).toBeEnabled();
    });
  });

  test('o botão de visualizar senha alterna o tipo entre password e text', async () => {
    const user = userEvent.setup();

    renderLogin();

    const passwordInput = screen.getByLabelText(/^senha$/i);
    expect(passwordInput).toHaveAttribute('type', 'password');

    const toggleButton = screen.getByRole('button', { name: /exibir senha/i });
    await user.click(toggleButton);

    expect(passwordInput).toHaveAttribute('type', 'text');
    expect(screen.getByRole('button', { name: /ocultar senha/i })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /ocultar senha/i }));
    expect(passwordInput).toHaveAttribute('type', 'password');
  });

  test('impedir envio vazio pode ser verificado pelo contrato do formulário', () => {
    renderLogin();

    const usernameInput = screen.getByLabelText(/^usuário$/i);
    const passwordInput = screen.getByLabelText(/^senha$/i);

    expect(usernameInput).toBeRequired();
    expect(passwordInput).toBeRequired();
  });
});
