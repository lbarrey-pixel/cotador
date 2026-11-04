import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import type { Proposta } from "./tipos";

const proposta: Proposta = {
  id: 7,
  numero: "COT-2026-00007",
  cliente: "Horizonte Redes Ltda",
  cnpj: "",
  avisos: [],
  itens: [
    {
      n: 1, descricao_original: "Switch 24p gigabit", quantidade: 4, unidade: "UN", produto_id: 2,
      produto_codigo: "SW24", produto_descricao: "Switch 24 portas", confianca: "alta", origem: "modelo",
      motivo: "mesma especificação", preco_un_centavos: 167700,
      candidatos: [
        { produto_id: 2, codigo: "SW24", descricao: "Switch 24 portas", similaridade: 0.8, descartado_por: null },
        { produto_id: 3, codigo: "SW48", descricao: "Switch 48 portas", similaridade: 0.6, descartado_por: "portas" },
      ],
    },
  ],
};

const json = (corpo: unknown) => new Response(JSON.stringify(corpo), { status: 200 });

afterEach(() => vi.restoreAllMocks());

describe("App", () => {
  it("lê o pedido e mostra itens com confiança e candidatos", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json(proposta));
    render(<App />);
    await userEvent.type(screen.getByLabelText("Pedido do cliente"), "4x switch 24p");
    await userEvent.click(screen.getByRole("button", { name: "Ler pedido" }));
    expect(await screen.findByText("COT-2026-00007")).toBeInTheDocument();
    expect(screen.getByText("alta")).toBeInTheDocument();
    const opcao = screen.getByRole("option", { name: /SW48.*diverge em portas/ });
    expect(opcao).toBeDisabled();
  });

  it("troca o produto do item e envia o PUT", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(json(proposta));
    render(<App />);
    await userEvent.type(screen.getByLabelText("Pedido do cliente"), "x");
    await userEvent.click(screen.getByRole("button", { name: "Ler pedido" }));
    await screen.findByText("COT-2026-00007");

    fetchMock.mockResolvedValueOnce(json({ ...proposta.itens[0], produto_id: null, confianca: "nenhuma" }));
    await userEvent.selectOptions(screen.getByLabelText("Produto do item 1"), "");
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const [url, init] = fetchMock.mock.calls[1];
    expect(String(url)).toContain("/propostas/7/itens/1");
    expect(init?.method).toBe("PUT");
    expect(JSON.parse(String(init?.body))).toEqual({ produto_id: null });
    expect(await screen.findByText("sem match")).toBeInTheDocument();
  });

  it("mostra a mensagem de erro da API", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "nenhum item encontrado no pedido" }), { status: 422 }),
    );
    render(<App />);
    await userEvent.type(screen.getByLabelText("Pedido do cliente"), "oi");
    await userEvent.click(screen.getByRole("button", { name: "Ler pedido" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("nenhum item encontrado");
  });
});
