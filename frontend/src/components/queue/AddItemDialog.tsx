import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, BookOpen, Search, X, Code2 } from "lucide-react";
import { Dialog, DialogContent, DialogTitle, DialogTrigger, DialogClose } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { ProblemResult } from "./types";
import { priorityOptions } from "./constants";
import { PlatformIcon } from "./PlatformIcon";

export function AddItemDialog({ onCreate }: { onCreate: (data: any) => void }) {
  const [title, setTitle]               = useState("");
  const [description, setDescription]   = useState("");
  const [itemType, setItemType]         = useState("PROBLEM");
  const [priority, setPriority]         = useState("P2");
  const [platform, setPlatform]         = useState<string | undefined>(undefined);
  const [searchQuery, setSearchQuery]   = useState("");
  const [selectedProblem, setSelectedProblem] = useState<ProblemResult | null>(null);
  const [open, setOpen]                 = useState(false);

  // Busca de problemas filtrada pela plataforma selecionada
  const { data: searchResults = [] } = useQuery<ProblemResult[]>({
    queryKey: ["problem-search", searchQuery, platform],
    queryFn: async () => {
      if (!searchQuery || searchQuery.length < 2) return [];
      const params = new URLSearchParams({ q: searchQuery, limit: "8" });
      if (platform) params.set("platform", platform);
      const { data } = await api.get(`/problems/search?${params}`);
      return data;
    },
    enabled: searchQuery.length >= 2 && itemType === "PROBLEM" && !!platform,
  });

  const resetForm = () => {
    setTitle("");
    setDescription("");
    setPriority("P2");
    setItemType("PROBLEM");
    setPlatform(undefined);
    setSearchQuery("");
    setSelectedProblem(null);
  };

  const handleSubmit = () => {
    const finalTitle = selectedProblem
      ? selectedProblem.title
      : title.trim();
    if (!finalTitle) return;

    onCreate({
      title: finalTitle,
      description: description.trim() || null,
      item_type: itemType,
      priority,
      source_platform: itemType === "PROBLEM"
        ? (selectedProblem?.platform ?? platform ?? null)
        : null,
      linked_problem_id: selectedProblem?.id ?? null,
    });
    setOpen(false);
    resetForm();
  };

  const selectProblem = (p: ProblemResult) => {
    setSelectedProblem(p);
    if (p.platform && p.platform !== platform) setPlatform(p.platform);
    setSearchQuery("");
  };

  const handlePlatformChange = (newPlatform: string) => {
    if (newPlatform !== platform) {
      setSelectedProblem(null);
      setSearchQuery("");
    }
    setPlatform(newPlatform);
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) resetForm(); }}>
      <DialogTrigger asChild>
        <div
          role="button"
          tabIndex={0}
          className="bg-[#dc143c] hover:bg-[#dc143c]/90 hover:-translate-y-0.5 shadow-md shadow-[#dc143c]/10 text-white text-[12px] font-semibold gap-2 h-9 px-5 transition-all rounded-lg border border-[#dc143c]/30 inline-flex items-center justify-center cursor-pointer active:scale-95 duration-200"
        >
          <Plus className="w-3.5 h-3.5" strokeWidth={2.5} />
          Novo Item
        </div>
      </DialogTrigger>

      <DialogContent className="bg-[#080808]/99 backdrop-blur-2xl border border-white/[0.09] text-white w-[95vw] sm:max-w-lg rounded-2xl p-0 overflow-hidden mx-auto max-h-[90vh] flex flex-col shadow-[0_24px_64px_rgba(0,0,0,0.65)]">
        {/* Cabeçalho */}
        <div className="px-6 py-4 border-b border-white/[0.07] shrink-0">
          <DialogTitle className="text-[15px] text-white font-bold tracking-tight">
            Criar Novo Item
          </DialogTitle>
          <p className="text-[11px] text-white/30 mt-0.5">Adicione uma questão ou sessão de estudo</p>
        </div>

        {/* Corpo */}
        <div className="overflow-y-auto flex-1 px-6 py-5 space-y-5">

          {/* Tipo */}
          <div className="space-y-2">
            <label className="text-[10px] uppercase text-white/30 font-bold tracking-widest">Tipo</label>
            <div className="flex gap-2">
              <button
                onClick={() => { setItemType("PROBLEM"); setSelectedProblem(null); }}
                className={[
                  "flex-1 py-2.5 rounded-xl flex items-center justify-center gap-2 text-[12px] font-bold tracking-wide transition-all duration-200 border",
                  itemType === "PROBLEM"
                    ? "bg-[#dc143c]/15 text-white border-[#dc143c]/40"
                    : "bg-white/[0.03] border-white/[0.06] text-white/35 hover:text-white/65 hover:bg-white/[0.06]",
                ].join(" ")}
              >
                <Code2 className="w-3.5 h-3.5" /> Questão
              </button>
              <button
                onClick={() => { setItemType("STUDY_SESSION"); setSelectedProblem(null); setPlatform(undefined); }}
                className={[
                  "flex-1 py-2.5 rounded-xl text-[12px] font-bold tracking-wide transition-all duration-200 flex items-center justify-center gap-2 border",
                  itemType === "STUDY_SESSION"
                    ? "bg-purple-600/15 text-white border-purple-500/35"
                    : "bg-white/[0.03] border-white/[0.06] text-white/35 hover:text-white/65 hover:bg-white/[0.06]",
                ].join(" ")}
              >
                <BookOpen className="w-3.5 h-3.5" /> Estudo
              </button>
            </div>
          </div>

          {/* Seção PROBLEM */}
          {itemType === "PROBLEM" && (
            <>
              {/* Plataforma */}
              <div className="space-y-2">
                <label className="text-[10px] uppercase text-white/30 font-bold tracking-widest">Plataforma</label>
                <div className="flex gap-2">
                  {[
                    { value: "CODEFORCES", label: "Codeforces" },
                    { value: "ATCODER",    label: "AtCoder"    },
                    { value: "CSES",       label: "CSES"       },
                  ].map((p) => (
                    <button
                      key={p.value}
                      onClick={() => handlePlatformChange(p.value)}
                      className={[
                        "flex-1 flex items-center justify-center gap-1.5 px-2 py-2.5 rounded-xl text-[11px] font-semibold border transition-all duration-200",
                        platform === p.value
                          ? "bg-white/[0.1] border-white/20 text-white"
                          : "bg-white/[0.02] border-white/[0.05] text-white/35 hover:text-white/65 hover:bg-white/[0.06]",
                      ].join(" ")}
                    >
                      <PlatformIcon platform={p.value} />
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Busca */}
              <div className="space-y-2">
                <label className="text-[10px] uppercase text-white/30 font-bold tracking-widest flex items-center gap-2">
                  Buscar Questão
                  {!platform && (
                    <span className="text-[9px] text-amber-400/60 normal-case tracking-normal font-normal">
                      (selecione uma plataforma primeiro)
                    </span>
                  )}
                </label>
                <div className="relative group">
                  <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-white/20 group-focus-within:text-primary transition-colors" />
                  <Input
                    disabled={!platform}
                    value={selectedProblem ? `${selectedProblem.platform_id} - ${selectedProblem.title}` : searchQuery}
                    onChange={(e) => { setSearchQuery(e.target.value); setSelectedProblem(null); }}
                    placeholder={platform ? "Busque por ID ou nome (ex: 1A, Theatre)" : "Selecione a plataforma acima"}
                    className="pl-10 h-10 bg-black/40 border-white/[0.09] text-white placeholder:text-white/18 rounded-xl text-[13px] disabled:opacity-40"
                  />
                  {selectedProblem && (
                    <button
                      onClick={() => { setSelectedProblem(null); setSearchQuery(""); }}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-white/25 hover:text-white/55 transition-colors"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                {/* Resultados de busca */}
                {searchResults.length > 0 && !selectedProblem && (
                  <div className="border border-white/[0.09] rounded-xl max-h-44 overflow-y-auto bg-[#0a0a0a]/98 shadow-xl">
                    {searchResults.map((p) => (
                      <button
                        key={p.id}
                        onClick={() => selectProblem(p)}
                        className="w-full px-4 py-2.5 text-left hover:bg-white/[0.04] transition-colors flex items-center gap-3 border-b border-white/[0.05] last:border-0"
                      >
                        <PlatformIcon platform={p.platform} />
                        <span className="text-white/35 font-mono text-[10px] bg-white/[0.04] px-1.5 py-0.5 rounded shrink-0">
                          {p.platform_id}
                        </span>
                        <span className="text-white/75 text-[12px] truncate font-medium">{p.title}</span>
                      </button>
                    ))}
                  </div>
                )}

                {/* Entrada manual removida conforme regra de plataforma */}
              </div>
            </>
          )}

          {/* Seção STUDY_SESSION */}
          {itemType === "STUDY_SESSION" && (
            <div className="space-y-2">
              <label className="text-[10px] uppercase text-white/30 font-bold tracking-widest">
                Objetivo do Estudo
              </label>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Ex: Estudar DP em árvores, Segment Tree lazy"
                className="h-10 bg-black/40 border-white/[0.09] text-white placeholder:text-white/18 rounded-xl text-[13px]"
              />
            </div>
          )}

          {/* Prioridade */}
          <div className="space-y-2">
            <label className="text-[10px] uppercase text-white/30 font-bold tracking-widest">Prioridade</label>
            <div className="flex gap-2">
              {priorityOptions.map((opt) => {
                const active = priority === opt.value;
                return (
                  <button
                    key={opt.value}
                    onClick={() => setPriority(opt.value)}
                    className="flex-1 flex flex-col items-center justify-center gap-1.5 py-2.5 rounded-xl text-[10px] font-bold tracking-widest uppercase border transition-all duration-200"
                    style={{
                      borderColor: active ? opt.color + "80" : "rgba(255,255,255,0.05)",
                      backgroundColor: active ? opt.color + "18" : "rgba(255,255,255,0.02)",
                      color: active ? "#fff" : "rgba(255,255,255,0.28)",
                    }}
                  >
                    <div
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: active ? opt.color : "rgba(255,255,255,0.15)" }}
                    />
                    {opt.value}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Descrição opcional */}
          <div className="space-y-2">
            <label className="text-[10px] uppercase text-white/30 font-bold tracking-widest">
              Descrição <span className="text-white/18 ml-1 font-normal normal-case tracking-normal">(opcional)</span>
            </label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Ex: Focar em DP com bitmask..."
              className="h-9 bg-black/40 border-white/[0.09] text-white placeholder:text-white/15 rounded-xl text-[12px]"
            />
          </div>
        </div>

        {/* Rodapé */}
        <div className="px-6 py-4 border-t border-white/[0.07] bg-black/15 flex justify-end gap-2.5 shrink-0">
          <DialogClose asChild>
            <Button
              variant="ghost"
              className="text-white/40 hover:text-white hover:bg-white/[0.04] rounded-lg text-[12px] font-medium h-9 px-5"
            >
              Cancelar
            </Button>
          </DialogClose>
          <Button
            onClick={handleSubmit}
            disabled={!title.trim() && !selectedProblem}
            className="bg-[#dc143c] hover:bg-[#dc143c]/90 hover:scale-[1.02] active:scale-95 text-white font-bold h-9 px-7 rounded-lg transition-all duration-200 disabled:opacity-35 text-[12px] border border-[#dc143c]/60 shadow-lg shadow-[#dc143c]/20"
          >
            Criar Item
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
