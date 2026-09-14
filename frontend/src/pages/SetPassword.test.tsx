import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { SetPassword } from './SetPassword';
import { api } from '@/lib/api';
import { ToastProvider } from '@/components/ui/toast';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('SetPassword Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  const renderSetPassword = (search = '?uid=uid123&token=tok456') => {
    return render(
      <ToastProvider>
        <MemoryRouter initialEntries={[`/set-password${search}`]}>
          <SetPassword />
        </MemoryRouter>
      </ToastProvider>
    );
  };

  test('1. ausência de uid ou token mostra "Link Inválido" e não chama a API', async () => {
    const user = userEvent.setup();
    const postSpy = vi.spyOn(api, 'post');

    renderSetPassword('?uid=&token=');

    await user.type(screen.getByLabelText(/^nova senha$/i), 'Password123!');
    await user.type(screen.getByLabelText(/^confirmar nova senha$/i), 'Password123!');
    await user.click(screen.getByRole('button', { name: /salvar nova senha/i }));

    expect(await screen.findByText('Link Inválido')).toBeInTheDocument();
    expect(postSpy).not.toHaveBeenCalled();
  });

  test('2. senhas diferentes mostram "Senhas Não Coincidem"', async () => {
    const user = userEvent.setup();
    const postSpy = vi.spyOn(api, 'post');

    renderSetPassword();

    await user.type(screen.getByLabelText(/^nova senha$/i), 'Password123!');
    await user.type(screen.getByLabelText(/^confirmar nova senha$/i), 'Different123!');
    await user.click(screen.getByRole('button', { name: /salvar nova senha/i }));

    expect(await screen.findByText('Senhas Não Coincidem')).toBeInTheDocument();
    expect(postSpy).not.toHaveBeenCalled();
  });

  test('3. senha com menos de oito caracteres é rejeitada', async () => {
    const user = userEvent.setup();
    const postSpy = vi.spyOn(api, 'post');

    renderSetPassword();

    await user.type(screen.getByLabelText(/^nova senha$/i), 'Pass1!');
    await user.type(screen.getByLabelText(/^confirmar nova senha$/i), 'Pass1!');
    await user.click(screen.getByRole('button', { name: /salvar nova senha/i }));

    expect(await screen.findByText('Senha Fora do Padrão')).toBeInTheDocument();
    expect(postSpy).not.toHaveBeenCalled();
  });

  test('4. senha sem letra é rejeitada', async () => {
    const user = userEvent.setup();
    const postSpy = vi.spyOn(api, 'post');

    renderSetPassword();

    await user.type(screen.getByLabelText(/^nova senha$/i), '12345678!');
    await user.type(screen.getByLabelText(/^confirmar nova senha$/i), '12345678!');
    await user.click(screen.getByRole('button', { name: /salvar nova senha/i }));

    expect(await screen.findByText('Senha Fora do Padrão')).toBeInTheDocument();
    expect(postSpy).not.toHaveBeenCalled();
  });

  test('5. senha sem número é rejeitada', async () => {
    const user = userEvent.setup();
    const postSpy = vi.spyOn(api, 'post');

    renderSetPassword();

    await user.type(screen.getByLabelText(/^nova senha$/i), 'Password!');
    await user.type(screen.getByLabelText(/^confirmar nova senha$/i), 'Password!');
    await user.click(screen.getByRole('button', { name: /salvar nova senha/i }));

    expect(await screen.findByText('Senha Fora do Padrão')).toBeInTheDocument();
    expect(postSpy).not.toHaveBeenCalled();
  });

  test('6. senha sem símbolo é rejeitada', async () => {
    const user = userEvent.setup();
    const postSpy = vi.spyOn(api, 'post');

    renderSetPassword();

    await user.type(screen.getByLabelText(/^nova senha$/i), 'Password123');
    await user.type(screen.getByLabelText(/^confirmar nova senha$/i), 'Password123');
    await user.click(screen.getByRole('button', { name: /salvar nova senha/i }));

    expect(await screen.findByText('Senha Fora do Padrão')).toBeInTheDocument();
    expect(postSpy).not.toHaveBeenCalled();
  });

  test('7. senha válida com caracteres ASCII é aceita', async () => {
    const user = userEvent.setup();
    const postSpy = vi.spyOn(api, 'post').mockResolvedValueOnce({ data: {} });

    renderSetPassword();

    await user.type(screen.getByLabelText(/^nova senha$/i), 'Password123!');
    await user.type(screen.getByLabelText(/^confirmar nova senha$/i), 'Password123!');
    await user.click(screen.getByRole('button', { name: /salvar nova senha/i }));

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalled();
    });
  });

  test('8. senha válida com letras Unicode acentuadas é aceita', async () => {
    const user = userEvent.setup();
    const postSpy = vi.spyOn(api, 'post').mockResolvedValueOnce({ data: {} });

    renderSetPassword();

    await user.type(screen.getByLabelText(/^nova senha$/i), 'SênhaVálida123!');
    await user.type(screen.getByLabelText(/^confirmar nova senha$/i), 'SênhaVálida123!');
    await user.click(screen.getByRole('button', { name: /salvar nova senha/i }));

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledWith('/auth/set-password', {
        uid: 'uid123',
        token: 'tok456',
        password: 'SênhaVálida123!',
      });
    });
  });

  test('9. envio correto para POST /auth/set-password com uid, token e password', async () => {
    const user = userEvent.setup();
    const postSpy = vi.spyOn(api, 'post').mockResolvedValueOnce({ data: {} });

    renderSetPassword('?uid=user_99&token=token_77');

    await user.type(screen.getByLabelText(/^nova senha$/i), 'MinhaSenha123#');
    await user.type(screen.getByLabelText(/^confirmar nova senha$/i), 'MinhaSenha123#');
    await user.click(screen.getByRole('button', { name: /salvar nova senha/i }));

    expect(postSpy).toHaveBeenCalledWith('/auth/set-password', {
      uid: 'user_99',
      token: 'token_77',
      password: 'MinhaSenha123#',
    });
  });

  test('10. sucesso mostra a confirmação visual', async () => {
    const user = userEvent.setup();
    vi.spyOn(api, 'post').mockResolvedValueOnce({ data: {} });

    renderSetPassword();

    await user.type(screen.getByLabelText(/^nova senha$/i), 'Password123!');
    await user.type(screen.getByLabelText(/^confirmar nova senha$/i), 'Password123!');
    await user.click(screen.getByRole('button', { name: /salvar nova senha/i }));

    expect(await screen.findByText('Senha Criada com Sucesso!')).toBeInTheDocument();
  });

  // Bloco isolado de fake timers para os testes de redirecionamento.
  // beforeEach/afterEach garantem restauração mesmo que o teste falhe.
  describe('11. redirecionamento via useEffect', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    test('11a. redireciona para /login exatamente após 2,5 s e não antes', async () => {
      vi.spyOn(api, 'post').mockResolvedValueOnce({ data: {} });

      renderSetPassword();

      const newPassInput = screen.getByLabelText(/^nova senha$/i);
      const confirmPassInput = screen.getByLabelText(/^confirmar nova senha$/i);
      const form = newPassInput.closest('form')!;

      fireEvent.change(newPassInput, { target: { value: 'Password123!' } });
      fireEvent.change(confirmPassInput, { target: { value: 'Password123!' } });
      fireEvent.submit(form);

      // Aguarda a Promise da API resolver (microtask queue)
      await act(async () => {
        await Promise.resolve();
      });

      // Sucesso visual aparece, mas redirecionamento ainda não ocorreu
      expect(screen.getByText('Senha Criada com Sucesso!')).toBeInTheDocument();
      expect(mockNavigate).not.toHaveBeenCalledWith('/login');

      // Avança exatamente 2,5 s — agora deve redirecionar
      act(() => {
        vi.advanceTimersByTime(2500);
      });

      expect(mockNavigate).toHaveBeenCalledWith('/login');
    });

    test('11b. desmontar antes de 2,5 s cancela o timer e não ocorre navegação', async () => {
      vi.spyOn(api, 'post').mockResolvedValueOnce({ data: {} });

      const { unmount } = renderSetPassword();

      const newPassInput = screen.getByLabelText(/^nova senha$/i);
      const confirmPassInput = screen.getByLabelText(/^confirmar nova senha$/i);
      const form = newPassInput.closest('form')!;

      fireEvent.change(newPassInput, { target: { value: 'Password123!' } });
      fireEvent.change(confirmPassInput, { target: { value: 'Password123!' } });
      fireEvent.submit(form);

      // Aguarda a Promise resolver para que success=true e o useEffect registre o timer
      await act(async () => {
        await Promise.resolve();
      });

      // Desmonta o componente antes do prazo — cleanup deve executar clearTimeout
      act(() => {
        unmount();
      });

      // Avança além de 2,5 s: o timer foi cancelado, navigate não deve ser chamado
      act(() => {
        vi.advanceTimersByTime(3000);
      });

      expect(mockNavigate).not.toHaveBeenCalledWith('/login');
    });
  });

  test('12. erro da API apresenta a mensagem retornada pelo backend', async () => {
    const user = userEvent.setup();
    vi.spyOn(api, 'post').mockRejectedValueOnce({
      response: { data: { message: 'Token de redefinição expirado.' } },
    });

    renderSetPassword();

    await user.type(screen.getByLabelText(/^nova senha$/i), 'Password123!');
    await user.type(screen.getByLabelText(/^confirmar nova senha$/i), 'Password123!');
    await user.click(screen.getByRole('button', { name: /salvar nova senha/i }));

    expect(await screen.findByText('Token de redefinição expirado.')).toBeInTheDocument();
  });

  test('13. erro sem mensagem conhecida utiliza a mensagem padrão', async () => {
    const user = userEvent.setup();
    vi.spyOn(api, 'post').mockRejectedValueOnce(new Error('Network failure'));

    renderSetPassword();

    await user.type(screen.getByLabelText(/^nova senha$/i), 'Password123!');
    await user.type(screen.getByLabelText(/^confirmar nova senha$/i), 'Password123!');
    await user.click(screen.getByRole('button', { name: /salvar nova senha/i }));

    expect(
      await screen.findByText('O link expirou ou já foi utilizado.')
    ).toBeInTheDocument();
  });

  // Teste 14 fortalecido: duas submissões do formulário são disparadas de forma
  // síncrona enquanto a primeira Promise ainda está pendente.
  // Isso comprova que loadingRef.current bloqueia a segunda chamada antes mesmo
  // de o estado `loading` (assíncrono) ser atualizado pelo React.
  test('14. duas submissões simultâneas do formulário devem disparar apenas uma requisição', async () => {
    let resolveApiPromise!: (value: unknown) => void;
    const apiPromise = new Promise((resolve) => {
      resolveApiPromise = resolve;
    });

    const postSpy = vi.spyOn(api, 'post').mockReturnValueOnce(apiPromise as ReturnType<typeof api.post>);

    renderSetPassword();

    const newPassInput = screen.getByLabelText(/^nova senha$/i);
    const confirmPassInput = screen.getByLabelText(/^confirmar nova senha$/i);
    const form = newPassInput.closest('form')!;

    // Preenche via fireEvent para controle síncrono total
    fireEvent.change(newPassInput, { target: { value: 'Password123!' } });
    fireEvent.change(confirmPassInput, { target: { value: 'Password123!' } });

    // Duas submissões SÍNCRONAS — antes de qualquer await.
    // Neste ponto React ainda não renderizou loading=true; somente
    // loadingRef.current=true (síncrono) pode bloquear o segundo handler.
    fireEvent.submit(form);
    fireEvent.submit(form);

    // Resolve a Promise e aguarda o ciclo de microtasks
    await act(async () => {
      resolveApiPromise({ data: {} });
    });

    // loadingRef bloqueou a segunda submissão: exatamente UMA chamada à API
    expect(postSpy).toHaveBeenCalledTimes(1);
  });

  test('15. botão de visualizar senha alterna os dois campos de forma coerente', async () => {
    const user = userEvent.setup();

    renderSetPassword();

    const newPassInput = screen.getByLabelText(/^nova senha$/i);
    const confirmPassInput = screen.getByLabelText(/^confirmar nova senha$/i);

    expect(newPassInput).toHaveAttribute('type', 'password');
    expect(confirmPassInput).toHaveAttribute('type', 'password');

    const toggleButton = screen.getByRole('button', { name: /exibir senha/i });
    await user.click(toggleButton);

    expect(newPassInput).toHaveAttribute('type', 'text');
    expect(confirmPassInput).toHaveAttribute('type', 'text');

    await user.click(screen.getByRole('button', { name: /ocultar senha/i }));

    expect(newPassInput).toHaveAttribute('type', 'password');
    expect(confirmPassInput).toHaveAttribute('type', 'password');
  });
});
