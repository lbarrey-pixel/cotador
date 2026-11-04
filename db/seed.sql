-- Gerado por scripts/gerar_seed.py a partir de db/catalogo.csv. Não edite à mão.

insert into produtos (id, codigo, descricao, atributos, preco_custo_centavos, ncm) values
  (1, 'NX-SW08G', 'Switch gerenciável 8 portas Gigabit NODAL NX-SW08G', '{"portas":"8"}'::jsonb, 38900, '85176255'),
  (2, 'NX-SW24G', 'Switch gerenciável 24 portas Gigabit NODAL NX-SW24G', '{"portas":"24"}'::jsonb, 129000, '85176255'),
  (3, 'NX-SW48G', 'Switch gerenciável 48 portas Gigabit NODAL NX-SW48G', '{"portas":"48"}'::jsonb, 289000, '85176255'),
  (4, 'NX-SW24P', 'Switch PoE 24 portas Gigabit 370W NODAL NX-SW24P', '{"portas":"24"}'::jsonb, 214500, '85176255'),
  (5, 'NX-AP6', 'Access point Wi-Fi 6 dual band teto NODAL NX-AP6', '{}'::jsonb, 57900, '85176255'),
  (6, 'NX-RT100', 'Roteador corporativo 5 portas Gigabit NODAL NX-RT100', '{"portas":"5"}'::jsonb, 46500, '85176255'),
  (7, 'VX-C5E-305', 'Cabo de rede UTP Cat5e 4 pares azul caixa 305m VERTEX', '{"categoria":"5e"}'::jsonb, 41000, '85444900'),
  (8, 'VX-C6-305', 'Cabo de rede UTP Cat6 4 pares azul caixa 305m VERTEX', '{"categoria":"6"}'::jsonb, 68500, '85444900'),
  (9, 'VX-C6-305C', 'Cabo de rede UTP Cat6 4 pares cinza caixa 305m VERTEX', '{"categoria":"6"}'::jsonb, 68500, '85444900'),
  (10, 'VX-C6A-305', 'Cabo de rede F/UTP Cat6A 4 pares caixa 305m VERTEX', '{"categoria":"6a"}'::jsonb, 112000, '85444900'),
  (11, 'VX-PC6-15', 'Patch cord Cat6 1,5m azul VERTEX', '{"categoria":"6"}'::jsonb, 1850, '85444200'),
  (12, 'VX-PC6-30', 'Patch cord Cat6 3m azul VERTEX', '{"categoria":"6"}'::jsonb, 2650, '85444200'),
  (13, 'VX-PC5E-15', 'Patch cord Cat5e 1,5m cinza VERTEX', '{"categoria":"5e"}'::jsonb, 1290, '85444200'),
  (14, 'VX-PP24', 'Patch panel 24 portas Cat6 19 polegadas VERTEX', '{"portas":"24","categoria":"6"}'::jsonb, 21900, '85366990'),
  (15, 'VX-PP48', 'Patch panel 48 portas Cat6 19 polegadas VERTEX', '{"portas":"48","categoria":"6"}'::jsonb, 39800, '85366990'),
  (16, 'VX-KJ6', 'Keystone fêmea RJ45 Cat6 VERTEX', '{"categoria":"6"}'::jsonb, 690, '85366990'),
  (17, 'VX-DIO12', 'Distribuidor interno óptico 12 fibras SC/APC VERTEX', '{"fibras":"12"}'::jsonb, 18700, '90019010'),
  (18, 'VX-CFO12', 'Cabo óptico monomodo 12 fibras indoor/outdoor metro VERTEX', '{"fibras":"12"}'::jsonb, 1450, '85447090'),
  (19, 'AR-DJ1C20', 'Disjuntor monopolar curva C 20A ARCA', '{"polos":"1","amperagem":"20"}'::jsonb, 1480, '85362000'),
  (20, 'AR-DJ1C32', 'Disjuntor monopolar curva C 32A ARCA', '{"polos":"1","amperagem":"32"}'::jsonb, 1590, '85362000'),
  (21, 'AR-DJ3C32', 'Disjuntor tripolar curva C 32A ARCA', '{"polos":"3","amperagem":"32"}'::jsonb, 7900, '85362000'),
  (22, 'AR-DJ3C63', 'Disjuntor tripolar curva C 63A ARCA', '{"polos":"3","amperagem":"63"}'::jsonb, 10400, '85362000'),
  (23, 'AR-DR2-40', 'Interruptor diferencial residual DR bipolar 40A 30mA ARCA', '{"polos":"2","amperagem":"40"}'::jsonb, 16500, '85365090'),
  (24, 'AR-CF25-100', 'Cabo flexível 2,5mm² 750V preto rolo 100m ARCA', '{"bitola":"2.5"}'::jsonb, 31500, '85444900'),
  (25, 'AR-CF40-100', 'Cabo flexível 4mm² 750V preto rolo 100m ARCA', '{"bitola":"4"}'::jsonb, 49800, '85444900'),
  (26, 'AR-CF60-100', 'Cabo flexível 6mm² 750V preto rolo 100m ARCA', '{"bitola":"6"}'::jsonb, 74200, '85444900'),
  (27, 'PL-FT12-5', 'Fonte chaveada 12V 5A bivolt PULSO', '{"tensao":"12","amperagem":"5"}'::jsonb, 4900, '85044090'),
  (28, 'PL-FT12-10', 'Fonte chaveada 12V 10A bivolt PULSO', '{"tensao":"12","amperagem":"10"}'::jsonb, 8700, '85044090'),
  (29, 'PL-FT24-5', 'Fonte chaveada 24V 5A bivolt PULSO', '{"tensao":"24","amperagem":"5"}'::jsonb, 7600, '85044090'),
  (30, 'PL-NB1500', 'Nobreak senoidal 1500VA 120V bateria interna PULSO', '{"tensao":"120"}'::jsonb, 189000, '85044040'),
  (31, 'PL-NB3000', 'Nobreak senoidal 3000VA 220V bateria interna PULSO', '{"tensao":"220"}'::jsonb, 412000, '85044040'),
  (32, 'PL-BT12-7', 'Bateria selada 12V 7Ah PULSO', '{"tensao":"12"}'::jsonb, 5900, '85072000'),
  (33, 'AL-CAM2D', 'Câmera IP dome 2MP lente 2,8mm IR 30m ALTAIR', '{"resolucao":"2"}'::jsonb, 19800, '85258929'),
  (34, 'AL-CAM4B', 'Câmera IP bullet 4MP lente 2,8mm IR 50m ALTAIR', '{"resolucao":"4"}'::jsonb, 31500, '85258929'),
  (35, 'AL-CAM8B', 'Câmera IP bullet 8MP lente 4mm IR 60m ALTAIR', '{"resolucao":"8"}'::jsonb, 58900, '85258929'),
  (36, 'AL-NVR16', 'Gravador NVR 16 canais PoE 4K ALTAIR', '{}'::jsonb, 146000, '85219090'),
  (37, 'AL-NVR32', 'Gravador NVR 32 canais 4K ALTAIR', '{}'::jsonb, 198000, '85219090'),
  (38, 'AL-HD4T', 'HD 4TB para videovigilância 7200rpm ALTAIR', '{"capacidade":"4tb"}'::jsonb, 79500, '84717012'),
  (39, 'AL-HD8T', 'HD 8TB para videovigilância 7200rpm ALTAIR', '{"capacidade":"8tb"}'::jsonb, 139000, '84717012'),
  (40, 'AL-CTL1', 'Controladora de acesso 1 porta com leitor de cartão ALTAIR', '{}'::jsonb, 41500, '85371090'),
  (41, 'AL-FEC', 'Fechadura eletroímã 600 libras com suporte ALTAIR', '{}'::jsonb, 23800, '83011000')
on conflict (id) do nothing;

insert into propostas (id, numero, referencia, cliente, cnpj, destino) values (1, 'COT-2026-00001', 'RFQ-0412', 'Horizonte Redes Ltda', '12345678000195', 'Campinas/SP') on conflict (id) do nothing;
insert into itens_proposta (proposta_id, n, descricao_original, quantidade, unidade, produto_id, confianca, origem, preco_un_centavos) values
  (1, 1, 'Switch 24p gigabit gerenciavel', 4, 'UN', 2, 'alta', 'modelo', 167700),
  (1, 2, 'Cabo UTP cat6 azul cx 305m', 6, 'CX', 8, 'alta', 'modelo', 89050),
  (1, 3, 'Patch cord cat6 1,5m', 120, 'UN', 11, 'media', 'modelo', 2405),
  (1, 4, 'Patch panel 24 portas', 4, 'UN', 14, 'alta', 'memoria_cliente', 28470)
on conflict (proposta_id, n) do nothing;

insert into propostas (id, numero, referencia, cliente, cnpj, destino) values (2, 'COT-2026-00002', '', 'Condomínio Parque das Acácias', '98765432000198', 'Belo Horizonte/MG') on conflict (id) do nothing;
insert into itens_proposta (proposta_id, n, descricao_original, quantidade, unidade, produto_id, confianca, origem, preco_un_centavos) values
  (2, 1, 'Camera IP 4MP bullet', 8, 'UN', 34, 'alta', 'modelo', 40950),
  (2, 2, 'NVR 16 canais', 1, 'UN', 36, 'media', 'modelo', 189800),
  (2, 3, 'HD 4TB p/ CFTV', 2, 'UN', 38, 'alta', 'modelo', 103350),
  (2, 4, 'Fonte 12V 10A', 2, 'UN', null, 'nenhuma', 'nenhuma', 0)
on conflict (proposta_id, n) do nothing;

insert into match_memoria (entrada_norm, escopo, produto_id, acertos) values
  ('patch panel 24 portas', 'cnpj:12345678', 14, 2),
  ('fonte 12v 5a', '', 27, 3)
on conflict do nothing;

select setval(pg_get_serial_sequence('produtos', 'id'), (select max(id) from produtos));
select setval(pg_get_serial_sequence('propostas', 'id'), (select max(id) from propostas));
