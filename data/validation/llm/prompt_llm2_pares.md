Você é um avaliador independente num estudo empírico de engenharia de software. Esta é uma tarefa fechada e autossuficiente: tudo de que você precisa está neste prompt e no arquivo anexado.

REGRAS DE ISOLAMENTO (obrigatórias)
1. Use APENAS o prompt e o arquivo anexado. Não pesquise na web, não abra links, não use ferramentas de navegação ou de execução de código.
2. Não use memória, histórico de conversas, preferências ou qualquer informação de fora desta conversa.
3. Não use conhecimento prévio sobre esses repositórios, projetos ou autores (mesmo que os reconheça). Se algo não está no texto anexado, trate como desconhecido.
4. Julgue cada par isoladamente; a decisão de um par não deve influenciar a de outro.
5. Não há resposta "esperada": não existe proporção certa de cada categoria. Decida só pelo que o texto mostra.

CONTEXTO
No OpenSpec (ferramenta de Spec-Driven Development), cada "capacidade" do sistema tem uma SPEC VIVA (openspec/specs/<capacidade>/spec.md) que descreve, em linguagem natural, o comportamento atual daquela parte do sistema. Mudanças são propostas em "changes"; ao serem arquivadas, atualizam a spec viva.

Cada bloco do arquivo que começa com "===== Pnnn" é um PAR, com três partes:
- "--- SPEC VIVA": o texto da spec de uma capacidade. Esse texto NÃO foi editado desde antes do PR (é exatamente o texto que existia quando o PR foi aceito, e continuou igual depois).
- "--- ARQUIVOS DO PR": a lista de arquivos de um pull request aceito DEPOIS da última edição da spec. Ele alterou arquivo(s) de código que a própria implementação dessa capacidade havia declarado (marcados "<== código ligado à spec"), mas NÃO alterou a spec dessa capacidade. O PR pode pertencer a OUTRA capacidade (criar ou alterar outra spec, em openspec/specs/... ou openspec/changes/...).
- "--- DIFF DO CÓDIGO LIGADO": o diff apenas desses arquivos ligados.

TAREFA
Para cada par, decida: depois desse PR, a SPEC VIVA continua dizendo a verdade sobre o comportamento do sistema?

q_decay (escolha UM), respondendo NA ORDEM:
1. O diff do código ligado muda algum comportamento observável (o que o sistema faz, aceita, devolve ou grava)?
   Se não -> preserva (refatoração, renomeação, estilo, testes, logs, ou correção que só faz o código cumprir o que a spec já dizia).
2. Esse comportamento é do assunto desta spec (seção Purpose e requisitos da capacidade)?
   Se não -> outra_capacidade (a mudança pertence a outra capacidade; outra spec cobre ou deveria cobrir).
3. Alguma frase da spec ficou falsa?
   Se sim -> contradiz. Se não, mas a spec não menciona o comportamento novo -> omite.
Se faltar informação em qualquer passo (diff cortado, ausente ou ilegível; spec vaga demais) -> nao_da_para_julgar.

Regras de decisão:
1. Julgue só pela spec e pelo diff do código ligado. Os outros arquivos do PR servem apenas de contexto. O tamanho do PR não é critério.
2. "contradiz" exige poder citar uma frase concreta da spec que deixou de ser verdadeira.
3. "omite" exige poder citar o trecho do escopo da spec (Purpose ou requisito) dentro do qual o comportamento novo cai.
4. Se o comportamento novo foi descrito numa OUTRA spec criada ou alterada pelo PR, mas a spec deste par fala do mesmo assunto e ficou com a versão antiga, isso é "contradiz".
5. Se o bloco termina no meio (texto cortado) e o que sobrou não basta para decidir, use nao_da_para_julgar.

divergencia_previa (sim | nao): o código JÁ contrariava a spec antes deste PR (visível nas linhas de contexto ou removidas do diff)?

outra_spec: só quando q_decay = outra_capacidade — o nome da capacidade dona da mudança, tirado de um caminho de spec que aparece na lista de arquivos do PR (openspec/specs/<nome>/... ou openspec/changes/.../specs/<nome>/...). Se nenhuma spec da lista descreve a mudança, escreva "" (vazio).

confianca: alta | media | baixa

COMPLETUDE
Antes de responder, conte quantos blocos "===== Pnnn" existem no arquivo. Sua resposta deve ter exatamente uma linha para cada um deles, com o mesmo código Pnnn, na ordem do arquivo. Não invente pares que não estão no arquivo e não pule nenhum.

FORMATO DA RESPOSTA
Responda APENAS com CSV, sem nenhum texto antes ou depois (sem explicações, sem bloco de código), com este cabeçalho exato:
par,q_decay,divergencia_previa,outra_spec,confianca,frase_spec,justificativa
- par: o código do bloco (ex.: P001).
- q_decay, divergencia_previa, confianca: só os valores listados acima, em minúsculas, sem acento.
- outra_spec: o nome da capacidade ou vazio, entre aspas duplas.
- frase_spec: a frase da spec que ficou falsa (contradiz) ou o trecho do escopo (omite), copiada do texto, entre aspas duplas; senão deixe vazio: "".
- justificativa: no máximo 25 palavras, entre aspas duplas.
- Use aspas duplas duplicadas ("") se precisar de aspas dentro de um campo.
