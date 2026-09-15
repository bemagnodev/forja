import React from 'react';

// Estende React.CSSProperties para permitir variáveis CSS customizadas (ex: '--ember-opacity') com type-safety absoluto
interface EmberStyleProperties extends React.CSSProperties {
  '--ember-opacity'?: number;
  '--ember-drift'?: string;
}

interface EmberParticle {
  id: number;
  size: number;
  left: number;
  duration: number;
  delay: number;
  opacity: number;
  blur: number;
  drift: number;
  boxShadow: string;
  color: string;
}

const EMBER_COUNT = 32;

// Paleta incandescente com gradientes radiais perfeitamente centralizados para manter o formato circular
const EMBER_COLORS = [
  'radial-gradient(circle at 50% 50%, #fff59d 0%, #ffb300 30%, #ff4500 70%, rgba(220, 20, 60, 0) 100%)',
  'radial-gradient(circle at 50% 50%, #ffecb3 0%, #ff8f00 35%, #e63946 75%, rgba(230, 57, 70, 0) 100%)',
  'radial-gradient(circle at 50% 50%, #ffffff 0%, #ffd54f 25%, #f77f00 65%, rgba(247, 127, 0, 0) 100%)',
  'radial-gradient(circle at 50% 50%, #ffe082 0%, #ff6f00 40%, #d00000 80%, rgba(208, 0, 0, 0) 100%)',
];

// Gerador congruencial linear simples (LCG) com semente fixa para obter distribuição pseudoaleatória determinística
function createDeterministicEmbers(count: number, seed: number = 42): EmberParticle[] {
  let s = seed;
  const nextPseudoRandom = () => {
    s = (s * 1664525 + 1013904223) % 4294967296;
    return s / 4294967296;
  };

  const particles: EmberParticle[] = [];
  for (let i = 0; i < count; i++) {
    const randSize = nextPseudoRandom();

    // Distribuição de tamanhos (evita partículas gigantes que parecem bolas):
    // ~25% pequenas (2–4px), ~65% médias (4–7px), ~10% ligeiramente maiores (8–10px)
    let size: number;
    if (randSize < 0.25) {
      size = Number((nextPseudoRandom() * 2 + 2).toFixed(2)); // 2–4px
    } else if (randSize < 0.90) {
      size = Number((nextPseudoRandom() * 3 + 4).toFixed(2)); // 4–7px
    } else {
      size = Number((nextPseudoRandom() * 2 + 8).toFixed(2)); // 8–10px
    }

    // Distribuição de posição horizontal ampla (3% a 97%):
    // ~70% espalhadas por toda a largura, ~15% na faixa esquerda (3%–33%), ~15% na faixa direita (67%–97%)
    const zoneRand = nextPseudoRandom();
    let left: number;
    if (zoneRand < 0.70) {
      left = Number((3 + nextPseudoRandom() * 94).toFixed(2)); // 3% a 97%
    } else if (zoneRand < 0.85) {
      left = Number((3 + nextPseudoRandom() * 30).toFixed(2)); // 3% a 33% (esquerda)
    } else {
      left = Number((67 + nextPseudoRandom() * 30).toFixed(2)); // 67% a 97% (direita)
    }

    const duration = Number((nextPseudoRandom() * 4 + 5.5).toFixed(2)); // 5.5s a 9.5s
    const delay = Number((nextPseudoRandom() * 6).toFixed(2)); // 0s a 6s
    const opacity = Number((nextPseudoRandom() * 0.3 + 0.7).toFixed(2)); // 0.7 a 1.0
    const blur = Number((nextPseudoRandom() * 0.5 + 0.2).toFixed(2)); // Blur baixo: 0.2px a 0.7px

    // Oscilação horizontal discreta entre -20px e +20px
    const drift = Number(((nextPseudoRandom() - 0.5) * 40).toFixed(2));

    const colorIndex = Math.floor(nextPseudoRandom() * EMBER_COLORS.length);
    const glowRadius = Number((size * 0.6).toFixed(1));
    const boxShadow = `0 0 ${glowRadius}px rgba(255, 140, 0, 0.5), 0 0 ${glowRadius * 1.2}px rgba(220, 20, 60, 0.3)`;

    particles.push({
      id: i,
      size,
      left,
      duration,
      delay,
      opacity,
      blur,
      drift,
      boxShadow,
      color: EMBER_COLORS[colorIndex],
    });
  }
  return particles;
}

// Lista imutável calculada uma única vez no nível do módulo (zero impurezas em tempo de renderização)
const STATIC_EMBERS: readonly EmberParticle[] = Object.freeze(createDeterministicEmbers(EMBER_COUNT));

export function EmberBackground() {
  return (
    <div
      className="absolute inset-0 z-0 overflow-hidden pointer-events-none select-none"
      aria-hidden="true"
    >
      <style>{`
        @keyframes floatUp {
          0% {
            transform: translateY(0) translateX(0) scale(1);
            opacity: 0;
          }
          20% {
            opacity: var(--ember-opacity, 0.8);
            transform: translateY(-20vh) translateX(calc(var(--ember-drift, 0px) * 0.4)) scale(0.95);
          }
          55% {
            opacity: var(--ember-opacity, 0.8);
            transform: translateY(-55vh) translateX(calc(var(--ember-drift, 0px) * -0.3)) scale(0.85);
          }
          80% {
            opacity: calc(var(--ember-opacity, 0.8) * 0.7);
            transform: translateY(-80vh) translateX(calc(var(--ember-drift, 0px) * 0.7)) scale(0.75);
          }
          100% {
            transform: translateY(-105vh) translateX(var(--ember-drift, 0px)) scale(0.7);
            opacity: 0;
          }
        }

        @media (prefers-reduced-motion: reduce) {
          .ember-particle {
            animation: none !important;
            opacity: 0.25 !important;
            transform: translateY(-20vh) scale(0.8) !important;
          }
        }
      `}</style>

      {/* Gradiente inferior característico da Forja */}
      <div className="absolute bottom-0 w-full h-[50vh] bg-gradient-to-t from-black via-[#dc143c]/10 to-transparent" />

      {/* Partículas de brasas */}
      {STATIC_EMBERS.map((ember) => {
        const emberStyle: EmberStyleProperties = {
          width: `${ember.size}px`,
          height: `${ember.size}px`,
          left: `${ember.left}%`,
          filter: `blur(${ember.blur}px)`,
          background: ember.color,
          boxShadow: ember.boxShadow,
          animation: `floatUp ${ember.duration}s linear ${ember.delay}s infinite`,
          '--ember-opacity': ember.opacity,
          '--ember-drift': `${ember.drift}px`,
        };

        return (
          <div
            key={ember.id}
            data-testid="ember-particle"
            className="ember-particle absolute bottom-[-20px] rounded-full mix-blend-screen opacity-0"
            style={emberStyle}
          />
        );
      })}
    </div>
  );
}
