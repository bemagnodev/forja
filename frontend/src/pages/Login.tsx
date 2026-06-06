import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Sword } from 'lucide-react';

export function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const resp = await api.post('/token', { username, password });
      login(resp.data.access, resp.data.refresh);
      navigate('/');
    } catch (err) {
      alert("Erro no login. Verifique suas credenciais.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen w-full flex-col items-center justify-center bg-black text-foreground relative overflow-hidden">
      {/* Background Decorativo */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-red-900/15 rounded-full blur-[120px] pointer-events-none" />
      
      <div className="z-10 w-full max-w-sm px-4">
        <div className="flex flex-col items-center mb-10">
          <div className="w-16 h-16 bg-red-950/50 rounded-2xl border border-red-500/30 flex items-center justify-center mb-6 shadow-[0_0_40px_rgba(220,38,38,0.2)] relative">
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-red-500/20 to-transparent" />
            <Sword className="w-8 h-8 text-red-500 relative z-10" />
          </div>
          <h1 className="text-4xl font-black tracking-tight text-white mb-2">A FORJA</h1>
          <p className="text-zinc-400 text-sm font-medium tracking-widest uppercase">Área de Membros</p>
        </div>

        <div className="bg-zinc-950/80 backdrop-blur-xl border border-zinc-800/50 rounded-2xl p-6 shadow-2xl relative">
          <div className="absolute inset-x-0 -top-px h-px bg-gradient-to-r from-transparent via-red-500/50 to-transparent" />
          <form onSubmit={handleLogin} className="space-y-5">
            <div className="space-y-2">
              <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Usuário</label>
              <input
                type="text"
                className="w-full rounded-xl border border-zinc-800 bg-zinc-900/50 px-4 py-3 text-white outline-none placeholder:text-zinc-600 focus:border-red-500/50 focus:bg-zinc-900 transition-all"
                placeholder="Ex: membro1"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Senha</label>
              <input
                type="password"
                className="w-full rounded-xl border border-zinc-800 bg-zinc-900/50 px-4 py-3 text-white outline-none placeholder:text-zinc-600 focus:border-red-500/50 focus:bg-zinc-900 transition-all"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <Button 
              type="submit" 
              disabled={loading}
              className="w-full mt-2 bg-red-600 hover:bg-red-700 text-white font-bold py-6 rounded-xl transition-all shadow-[0_0_20px_rgba(220,38,38,0.2)] hover:shadow-[0_0_30px_rgba(220,38,38,0.4)] border border-red-500/50"
            >
              {loading ? 'Acessando...' : 'Entrar na Forja'}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
