import { UserRound, Users } from 'lucide-react';

export function ContestIdentity({ platform, virtual }: { platform: string; virtual: boolean }) {
  const team = platform === 'CF_GYM';
  const Icon = team ? Users : UserRound;
  const cf = platform.startsWith('CF_');
  return <div className="flex min-w-0 items-center gap-2 text-[10px] font-medium text-zinc-500">
    {cf ? <img src="/logos/code-forces.png" alt="Codeforces" title={team ? 'Codeforces Gym' : 'Codeforces regular'} className="size-4 shrink-0 object-contain" />
      : <span>{platform === 'ATCODER' ? 'AtCoder' : platform}</span>}
    <span className="inline-flex items-center gap-1.5 rounded border border-zinc-800 bg-zinc-950/60 px-1.5 py-1 text-zinc-300"><Icon className="size-3" />{team ? 'Equipe' : 'Individual'}</span>
    <span className="size-0.5 rounded-full bg-zinc-700" />
    <span>{virtual ? 'Virtual' : 'Oficial'}</span>
  </div>;
}
