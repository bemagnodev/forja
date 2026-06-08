import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Eye, EyeOff } from 'lucide-react';
import { useToast } from '@/components/ui/toast';

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
    } catch (err) {
      toast({
        title: "Acesso Negado",
        description: "Credenciais inválidas. As portas da Forja permanecem fechadas.",
        type: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  const embers = Array.from({ length: 50 }).map((_, i) => {
    const size = Math.random() * 5 + 2;
    const left = Math.random() * 100;
    const duration = Math.random() * 4 + 4;
    const delay = Math.random() * 5;
    return (
      <div
        key={i}
        className="absolute bottom-[-20px] rounded-full blur-[1px] mix-blend-screen opacity-0"
        style={{
          width: `${size}px`,
          height: `${size}px`,
          left: `${left}%`,
          background: `radial-gradient(circle, #dc143c 0%, rgba(220, 20, 60, 0.4) 50%, transparent 100%)`,
          animation: `floatUp ${duration}s linear ${delay}s infinite`,
        }}
      />
    );
  });

  return (
    <div className="flex min-h-screen w-full flex-col items-center justify-center bg-black text-foreground relative overflow-hidden">
      <style>{`
        @keyframes floatUp {
          0% { transform: translateY(0) scale(1) rotate(0deg); opacity: 0; }
          10% { opacity: 0.8; }
          80% { opacity: 0.8; }
          100% { transform: translateY(-100vh) scale(0) rotate(360deg); opacity: 0; }
        }
      `}</style>
      
      {/* Efeito de Fogo/Brasas (Background) */}
      <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
        <div className="absolute bottom-0 w-full h-[50vh] bg-gradient-to-t from-black via-[#dc143c]/10 to-transparent" />
        {embers}
      </div>
      
      <div className="z-10 w-full max-w-sm px-4 relative">
        <div className="flex flex-col items-center mb-10">
          <img src="/logos/sword.png" alt="A Forja Logo" className="w-16 h-16 object-contain mb-4 relative z-10" />
          <h1 className="text-4xl font-black tracking-tight text-white mb-2">A FORJA</h1>
          <p className="text-zinc-400 text-xs text-center font-medium tracking-widest uppercase">Sistema de Treinamento<br/>de Programação Competitiva</p>
        </div>

        <div className="bg-zinc-950/80 backdrop-blur-xl border border-zinc-800/80 rounded-2xl p-6 shadow-2xl relative">
          <form onSubmit={handleLogin} className="space-y-5">
            <div className="space-y-2">
              <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Usuário</label>
              <input
                type="text"
                className="w-full rounded-xl border border-zinc-800 bg-zinc-900/80 px-4 py-3 text-white outline-none placeholder:text-zinc-600 focus:border-red-500/70 focus:bg-zinc-900 focus:shadow-[0_0_15px_rgba(220,38,38,0.2)] transition-all"
                placeholder="Ex: membro1"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2 relative">
              <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Senha</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  className="w-full rounded-xl border border-zinc-800 bg-zinc-900/80 px-4 py-3 pr-12 text-white outline-none placeholder:text-zinc-600 focus:border-red-500/70 focus:bg-zinc-900 focus:shadow-[0_0_15px_rgba(220,38,38,0.2)] transition-all"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
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
              className="w-full mt-4 bg-primary hover:bg-primary/90 text-white font-bold py-6 rounded-xl transition-all uppercase tracking-widest text-sm"
            >
              {loading ? 'Acessando...' : 'Entrar'}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
