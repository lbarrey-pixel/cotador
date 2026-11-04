export const reais = (centavos: number): string =>
  (centavos / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

/** "12,50" ou "1.234,5" -> centavos; texto inválido vira null. */
export function paraCentavos(texto: string): number | null {
  const limpo = texto.trim().replace(/\./g, "").replace(",", ".");
  if (!/^\d+(\.\d{1,2})?$/.test(limpo)) return null;
  return Math.round(parseFloat(limpo) * 100);
}

export const ROTULO_CONFIANCA = {
  alta: "alta",
  media: "média",
  baixa: "baixa",
  nenhuma: "sem match",
} as const;
