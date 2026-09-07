import React, { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Eye, EyeOff, CheckCircle2 } from 'lucide-react';
import { useToast } from '@/components/ui/toast';

export function SetPassword() {
  const [searchParams] = useSearchParams();
  const uid = searchParams.get('uid') || '';
  const token = searchParams.get('token') || '';

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const navigate = useNavigate();
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!uid || !token) {
      toast({
        title: "Link Inválido",
        description: "O link de convite está incompleto ou corrompido.",
        type: "error",
      });
      return;
    }

    if (password !== confirmPassword) {
      toast({
        title: "Senhas Não Coincidem",
        description: "A confirmação de senha deve ser idêntica à senha digitada.",
        type: "error",
      });
      return;
    }

    if (password.length < 6) {
      toast({
        title: "Senha Curta",
        description: "A senha precisa ter pelo menos 6 caracteres.",
        type: "error",
      });
      return;
    }

    setLoading(true);
    try {
      await api.post('/auth/set-password', {
        uid,
        token,
        password,
      });

      setSuccess(true);
      toast({
        title: "Senha Definida!",
        description: "Sua senha foi cadastrada com sucesso. Redirecionando para o login...",
        type: "success",
      });

      setTimeout(() => {
        navigate('/login');
      }, 2500);
    } catch (err: any) {
      const errorMsg = err.response?.data?.message || "O link expirou ou já foi utilizado.";
      toast({
        title: "Erro ao Definir Senha",
        description: errorMsg,
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
      
      {/* Background Embers */}
      <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
        <div className="absolute bottom-0 w-full h-[50vh] bg-gradient-to-t from-black via-[#dc143c]/10 to-transparent" />
        {embers}
      </div>
      
      <div className="z-10 w-full max-w-sm px-4 relative">
        <div className="flex flex-col items-center mb-10">
          <img src="/logos/sword.png" alt="A Forja Logo" className="w-16 h-16 object-contain mb-4 relative z-10" />
          <h1 className="text-4xl font-black tracking-tight text-white mb-2">A FORJA</h1>
          <p className="text-zinc-400 text-xs text-center font-medium tracking-widest uppercase">
            Definição de Senha
          </p>
        </div>

        <div className="bg-zinc-950/80 backdrop-blur-xl border border-zinc-800/80 rounded-2xl p-6 shadow-2xl relative">
          {success ? (
            <div className="py-8 flex flex-col items-center text-center space-y-4">
              <CheckCircle2 className="w-12 h-12 text-green-500 animate-bounce" />
              <h2 className="text-lg font-bold text-white">Senha Criada com Sucesso!</h2>
              <p className="text-sm text-zinc-400">Você será redirecionado para a tela de login...</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2 relative">
                <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Nova Senha</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    className="w-full rounded-xl border border-zinc-800 bg-zinc-900/80 px-4 py-3 pr-12 text-white outline-none placeholder:text-zinc-600 focus:border-red-500/70 focus:bg-zinc-900 focus:shadow-[0_0_15px_rgba(220,38,38,0.2)] transition-all"
                    placeholder="Mínimo 6 caracteres"
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

              <div className="space-y-2 relative">
                <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Confirmar Nova Senha</label>
                <input
                  type={showPassword ? 'text' : 'password'}
                  className="w-full rounded-xl border border-zinc-800 bg-zinc-900/80 px-4 py-3 text-white outline-none placeholder:text-zinc-600 focus:border-red-500/70 focus:bg-zinc-900 focus:shadow-[0_0_15px_rgba(220,38,38,0.2)] transition-all"
                  placeholder="Repita a nova senha"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
              </div>

              <Button 
                type="submit" 
                disabled={loading}
                className="w-full mt-4 bg-primary hover:bg-primary/90 text-white font-bold py-6 rounded-xl transition-all uppercase tracking-widest text-sm"
              >
                {loading ? 'Salvando...' : 'Salvar Nova Senha'}
              </Button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
