import { useState } from "react";
import { ChevronDown, Copy } from "lucide-react";

export interface PublishedPrompt {
  version: string;
  hash: string;
  label: string;
  description: string;
  text: string;
}

export function PromptDetails({ prompts }: { prompts: PublishedPrompt[] }) {
  const [selectedHash, setSelectedHash] = useState("");
  const [copyStatus, setCopyStatus] = useState("");
  const prompt = prompts.find(item => item.hash === selectedHash) || prompts[0];
  if (!prompt) return null;
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(prompt.text);
      setCopyStatus("Prompt copiado.");
    } catch {
      setCopyStatus("Não foi possível copiar. Selecione o texto para copiar manualmente.");
    }
  };
  return <details className="rounded-xl border border-zinc-800 bg-zinc-900/30 p-5 sm:p-6">
    <summary className="flex cursor-pointer list-none items-center justify-between text-sm text-zinc-300 outline-none focus-visible:ring-2 focus-visible:ring-primary">Técnica e prompt<ChevronDown className="size-4" /></summary>
    <div className="mt-5 space-y-4 text-sm text-zinc-400">
      {prompts.length > 1 && <label className="block text-xs">Estratégia do prompt<select aria-label="Estratégia do prompt" className="mt-2 block max-w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-zinc-200" value={prompt.hash} onChange={event => { setSelectedHash(event.target.value); setCopyStatus(""); }}>
        {prompts.map(item => <option key={item.hash} value={item.hash}>{item.label}</option>)}
      </select></label>}
      <h3 className="font-medium text-zinc-100">{prompt.label}</h3>
      <p>{prompt.description}</p>
      <p className="text-xs leading-relaxed">Instrução de sistema efetivamente usada, com a taxonomia preenchida. Cada enunciado preparado foi enviado separadamente, na mensagem do usuário; os enunciados não são publicados aqui.</p>
      <p className="break-all font-mono text-[11px] text-zinc-500">Versão {prompt.version} · SHA-256 {prompt.hash}</p>
      <button type="button" onClick={() => void copy()} className="inline-flex items-center gap-2 rounded-md border border-zinc-700 px-3 py-2 text-xs text-zinc-200 hover:border-forja/60 focus-visible:ring-2 focus-visible:ring-primary"><Copy className="size-3.5" />Copiar prompt</button>
      <p role="status" className="text-xs text-zinc-400">{copyStatus}</p>
      <pre aria-label="Prompt completo" className="max-h-[32rem] overflow-auto whitespace-pre-wrap break-words rounded-lg border border-zinc-800 bg-zinc-950 p-4 text-xs leading-relaxed text-zinc-300">{prompt.text}</pre>
    </div>
  </details>;
}
