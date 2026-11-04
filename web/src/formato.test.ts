import { paraCentavos, reais } from "./formato";

describe("formato", () => {
  it("converte texto em centavos aceitando vírgula e ponto de milhar", () => {
    expect(paraCentavos("12,50")).toBe(1250);
    expect(paraCentavos("1.234,5")).toBe(123450);
    expect(paraCentavos("7")).toBe(700);
  });

  it("rejeita o que não é valor", () => {
    expect(paraCentavos("abc")).toBeNull();
    expect(paraCentavos("1,234")).toBeNull();
    expect(paraCentavos("")).toBeNull();
  });

  it("formata em reais", () => {
    expect(reais(167700).replace(/\s/g, " ")).toBe("R$ 1.677,00");
  });
});
