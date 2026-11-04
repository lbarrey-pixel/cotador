export interface Candidato {
  produto_id: number;
  codigo: string;
  descricao: string;
  similaridade: number;
  descartado_por: string | null;
}

export interface Item {
  n: number;
  descricao_original: string;
  quantidade: number;
  unidade: string;
  produto_id: number | null;
  produto_codigo: string;
  produto_descricao: string;
  confianca: "alta" | "media" | "baixa" | "nenhuma";
  origem: string;
  motivo: string;
  preco_un_centavos: number;
  candidatos: Candidato[];
}

export interface Proposta {
  id: number;
  numero: string;
  cliente: string;
  cnpj: string;
  avisos: string[];
  itens: Item[];
}

export interface Produto {
  id: number;
  codigo: string;
  descricao: string;
}
