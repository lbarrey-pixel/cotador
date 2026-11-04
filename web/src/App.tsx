import { useState } from "react";
import { atualizarItem, buscarProdutos, extrair, gerarCsv } from "./api";
import { paraCentavos, reais, ROTULO_CONFIANCA } from "./formato";
import type { Item, Produto, Proposta } from "./tipos";

function baixar(blob: Blob, nome: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nome;
  a.click();
  URL.revokeObjectURL(url);
}

interface LinhaProps {
  item: Item;
  onEscolher: (n: number, produtoId: number | null) => void;
  onPreco: (n: number, centavos: number) => void;
}

function LinhaItem({ item, onEscolher, onPreco }: LinhaProps) {
  const [extras, setExtras] = useState<Produto[]>([]);
  const [busca, setBusca] = useState("");
  const [preco, setPreco] = useState((item.preco_un_centavos / 100).toFixed(2).replace(".", ","));

  const noCatalogo = new Set(item.candidatos.map((c) => c.produto_id));
  const buscar = async () => {
    if (busca.trim()) setExtras((await buscarProdutos(busca)).filter((p) => !noCatalogo.has(p.id)));
  };

  return (
    <tr>
      <td>{item.n}</td>
      <td>
        {item.descricao_original}
        {item.motivo && <small className="motivo">{item.motivo}</small>}
      </td>
      <td className="num">
        {item.quantidade} {item.unidade}
      </td>
      <td>
        <select
          aria-label={`Produto do item ${item.n}`}
          value={item.produto_id ?? ""}
          onChange={(e) => onEscolher(item.n, e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">— sem produto —</option>
          {item.candidatos.map((c) => (
            <option key={c.produto_id} value={c.produto_id} disabled={!!c.descartado_por}>
              {c.codigo} · {c.descricao}
              {c.descartado_por ? ` (diverge em ${c.descartado_por})` : ""}
            </option>
          ))}
          {extras.map((p) => (
            <option key={p.id} value={p.id}>
              {p.codigo} · {p.descricao}
            </option>
          ))}
        </select>
        <div className="busca">
          <input
            placeholder="buscar no catálogo"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && buscar()}
          />
        </div>
      </td>
      <td>
        <span className={`selo ${item.confianca}`}>{ROTULO_CONFIANCA[item.confianca]}</span>
      </td>
      <td className="num">
        <input
          className="preco"
          aria-label={`Preço do item ${item.n}`}
          value={preco}
          onChange={(e) => setPreco(e.target.value)}
          onBlur={() => {
            const c = paraCentavos(preco);
            if (c !== null && c !== item.preco_un_centavos) onPreco(item.n, c);
          }}
        />
        <small>{reais(item.preco_un_centavos)}</small>
      </td>
    </tr>
  );
}

export default function App() {
  const [texto, setTexto] = useState("");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [proposta, setProposta] = useState<Proposta | null>(null);
  const [frete, setFrete] = useState("0");
  const [prazo, setPrazo] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");

  const executar = async (fn: () => Promise<void>) => {
    setErro("");
    setCarregando(true);
    try {
      await fn();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "erro inesperado");
    } finally {
      setCarregando(false);
    }
  };

  const trocarItem = (novo: Item) =>
    setProposta((p) => p && { ...p, itens: p.itens.map((i) => (i.n === novo.n ? { ...i, ...novo } : i)) });

  const ler = () => executar(async () => setProposta(await extrair(texto, arquivo)));
  const escolher = (n: number, produtoId: number | null) =>
    executar(async () => trocarItem(await atualizarItem(proposta!.id, n, { produto_id: produtoId })));
  const mudarPreco = (n: number, centavos: number) =>
    executar(async () => trocarItem(await atualizarItem(proposta!.id, n, { preco_un_centavos: centavos })));
  const csv = () =>
    executar(async () => {
      const blob = await gerarCsv(proposta!.id, paraCentavos(frete) ?? 0, prazo);
      baixar(blob, `${proposta!.numero}.csv`);
    });

  return (
    <main>
      <h1>Cotador</h1>
      <p className="sub">Cole o pedido do cliente ou envie o arquivo (e-mail, planilha, PDF).</p>

      <section className="entrada">
        <textarea
          aria-label="Pedido do cliente"
          rows={6}
          placeholder={"4x switch 24 portas gigabit\n6 cx cabo utp cat6 azul 305m"}
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
        />
        <div className="acoes">
          <input
            type="file"
            aria-label="Arquivo do pedido"
            accept=".eml,.msg,.xlsx,.csv,.pdf,.txt"
            onChange={(e) => setArquivo(e.target.files?.[0] ?? null)}
          />
          <button onClick={ler} disabled={carregando || (!texto.trim() && !arquivo)}>
            {carregando ? "Lendo…" : "Ler pedido"}
          </button>
        </div>
      </section>

      {erro && <p role="alert" className="erro">{erro}</p>}

      {proposta && (
        <section>
          <h2>
            {proposta.numero} <small>{proposta.cliente || "cliente não identificado"} {proposta.cnpj}</small>
          </h2>
          {proposta.avisos.map((a) => (
            <p key={a} className="aviso">{a}</p>
          ))}
          <table>
            <thead>
              <tr><th>#</th><th>Pedido do cliente</th><th>Qtd</th><th>Produto</th><th>Confiança</th><th>Preço un.</th></tr>
            </thead>
            <tbody>
              {proposta.itens.map((i) => (
                <LinhaItem key={`${i.n}-${i.produto_id}`} item={i} onEscolher={escolher} onPreco={mudarPreco} />
              ))}
            </tbody>
          </table>
          <div className="rodape">
            <label>
              Frete (R$)
              <input value={frete} onChange={(e) => setFrete(e.target.value)} />
            </label>
            <label>
              Prazo de entrega
              <input value={prazo} onChange={(e) => setPrazo(e.target.value)} />
            </label>
            <button onClick={csv} disabled={carregando}>Gerar CSV</button>
          </div>
        </section>
      )}
    </main>
  );
}
