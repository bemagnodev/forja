import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';

export function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const resp = await api.post('/token', { username, password });
      login(resp.data.access, resp.data.refresh);
      navigate('/');
    } catch (err) {
      alert("Erro no login. Verifique suas credenciais.");
    }
  };

  return (
    <div className="flex h-screen w-full items-center justify-center bg-[#050505] text-foreground">
      <div className="w-full max-w-sm rounded-lg bg-[#111] border border-border p-8 shadow-2xl">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-amber-600">A Forja</h1>
          <p className="text-muted-foreground mt-2">Faça login para continuar</p>
        </div>
        <form onSubmit={handleLogin} className="space-y-6">
          <div className="space-y-2">
            <label className="text-sm font-medium">Usuário</label>
            <input
              type="text"
              className="w-full rounded-md border border-border bg-black/50 px-3 py-2 outline-none focus:border-primary transition-colors"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Senha</label>
            <input
              type="password"
              className="w-full rounded-md border border-border bg-black/50 px-3 py-2 outline-none focus:border-primary transition-colors"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <Button type="submit" className="w-full bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 text-white font-bold py-2 rounded-md transition-all">
            Entrar
          </Button>
        </form>
      </div>
    </div>
  );
}
