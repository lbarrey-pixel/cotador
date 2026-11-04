import type { Item, Produto, Proposta } from "./tipos";

const BASE = import.meta.env.VITE_API_URL ?? "/api";

async function ler<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const corpo = await r.json().catch(() => ({}));
    throw new Error(typeof corpo.detail === "string" ? corpo.detail : `erro ${r.status}`);
  }
  return r.json() as Promise<T>;
}

export async function extrair(texto: string, arquivo: File | null): Promise<Proposta> {
  const form = new FormData();
  form.set("texto", texto);
  if (arquivo) form.set("arquivo", arquivo);
  return ler(await fetch(`${BASE}/propostas/extrair`, { method: "POST", body: form }));
}

export async function atualizarItem(
  propostaId: number,
  n: number,
  corpo: { produto_id?: number | null; quantidade?: number; preco_un_centavos?: number },
): Promise<Item> {
  const r = await fetch(`${BASE}/propostas/${propostaId}/itens/${n}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  });
  return ler(r);
}

export async function buscarProdutos(q: string): Promise<Produto[]> {
  return ler(await fetch(`${BASE}/produtos?q=${encodeURIComponent(q)}&limite=10`));
}

export async function gerarCsv(propostaId: number, frete_centavos: number, prazo_entrega: string) {
  const r = await fetch(`${BASE}/propostas/${propostaId}/csv`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ frete_centavos, prazo_entrega }),
  });
  if (!r.ok) return ler<never>(r);
  return r.blob();
}
