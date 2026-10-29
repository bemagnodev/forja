import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import { useAuth } from '@/contexts/useAuth';
import { Button } from '@/components/ui/button';
import { Eye, EyeOff } from 'lucide-react';
import { useToast } from '@/components/ui/toast-context';

import { EmberBackground } from '@/components/effects/EmberBackground';

export function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const resp = await api.post('/token/pair', { username, password });
      login(resp.data.access, resp.data.refresh);
      navigate('/dashboard');
    } catch {
      toast({
        title: "Acesso Negado",
        description: "Credenciais inválidas. As portas da Forja permanecem fechadas.",
        type: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen w-full flex-col items-center justify-center bg-black text-foreground relative overflow-hidden">
      {/* Efeito de Fogo/Brasas (Background compartilhado) */}
      <EmberBackground />
      
      <div className="z-10 w-full max-w-sm px-4 relative">
        <div className="flex flex-col items-center mb-10">
          <img src="/logos/sword.png" alt="A Forja Logo" className="w-16 h-16 object-contain mb-4 relative z-10" />
          <h1 className="text-4xl font-black tracking-tight text-white mb-2">A FORJA</h1>
          <p className="text-zinc-400 text-xs text-center font-medium tracking-widest uppercase">Sistema de Treinamento<br/>de Programação Competitiva</p>
        </div>

        <div className="bg-zinc-950/80 backdrop-blur-xl border border-zinc-800/80 rounded-2xl p-6 shadow-2xl relative">
          <form onSubmit={handleLogin} className="space-y-5">
            <div className="space-y-2">
              <label htmlFor="username" className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Usuário</label>
              <input
                id="username"
                type="text"
                className="w-full rounded-xl border border-zinc-800 bg-zinc-900/80 px-4 py-3 text-white outline-none placeholder:text-zinc-600 focus:border-red-500/70 focus:bg-zinc-900 focus:shadow-[0_0_15px_rgba(220,38,38,0.2)] transition-all"
                placeholder="Ex: membro1"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2 relative">
              <label htmlFor="password" className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Senha</label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  className="w-full rounded-xl border border-zinc-800 bg-zinc-900/80 px-4 py-3 pr-12 text-white outline-none placeholder:text-zinc-600 focus:border-red-500/70 focus:bg-zinc-900 focus:shadow-[0_0_15px_rgba(220,38,38,0.2)] transition-all"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  aria-label={showPassword ? "Ocultar senha" : "Exibir senha"}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>
            <Button 
              type="submit" 
              disabled={loading}
              className="w-full mt-4 bg-primary hover:bg-zinc-800 text-white font-bold py-6 rounded-xl transition-all uppercase tracking-widest text-sm"
            >
              {loading ? 'Acessando...' : 'Entrar'}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
