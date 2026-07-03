<!--
Sync Impact Report:
- Version change: 2.0.0 → 2.1.0
- List of modified principles:
  - I. Local-First e Usuário Único (Updated to specify single Docker container deployment)
- Added sections: None
- Removed sections: None
- Templates requiring updates:
  - .specify/templates/plan-template.md: ✅ updated (no manual stack overrides needed)
  - .specify/templates/spec-template.md: ✅ updated (already technology-agnostic)
  - .specify/templates/tasks-template.md: ✅ updated (already supports Docker setup tasks)
- Follow-up TODOs: None
-->

# Extrator e Filtro de P&R Constitution

## Core Principles

### I. Local-First e Usuário Único
O sistema MUST ser executado inteiramente em ambiente local (localhost) utilizando um backend
local escrito em Python com FastAPI e um frontend em TypeScript com React, ambos empacotados e
executados em um único container Docker. Não deve haver dependência de serviços em nuvem ou
conexões externas de banco de dados. Mecanismos de autenticação, login ou gestão de perfis de
acesso não são necessários, focando em simplicidade, segurança e privacidade de dados local.

### II. Processamento Transparente de Arquivos
O processamento de arquivos MUST ser completamente transparente para o usuário. O sistema deve
listar visualmente todos os arquivos carregados para processamento, prover um log de execução
detalhado em tempo real na tela e destacar claramente os resultados mapeados e a contagem de
frequência de perguntas e respostas.

### III. Estética Premium e Micro-animações
A interface web MUST apresentar um design moderno, limpo e atraente desenvolvido com React,
TypeScript, Tailwind CSS e componentes da shadcn/ui. Devemos utilizar esquemas de cores
harmoniosos (como tons escuros/sleek dark mode ou paletas HSL customizadas), tipografia moderna
(Inter ou Outfit) e micro-animações (como transições de hover nos botões e listas, modais
dinâmicos e feedbacks visuais no carregamento de arquivos) para criar uma experiência premium.

### IV. Formatos de Exportação Duplos
Os resultados processados MUST ser exportáveis in dois formatos distintos e bem definidos: um
arquivo de texto (.txt) contendo o relatório estruturado legível por humanos (apropriado para Word
ou Google Docs) e um arquivo estruturado JSON contendo a lista completa de perguntas e respostas
com seus respectivos metadados para consumo programático.

### V. Mecanismo de Extração Modular
O algoritmo de extração, filtragem e contabilização de perguntas e respostas MUST ser desenvolvido
de forma desacoplada no backend FastAPI, mantendo o frontend React focado apenas na visualização
e controle. A estrutura de código de ambos frontend e backend MUST ser modular. A criação de
parsers, formatadores e instâncias de serviços principais em ambas as partes MUST utilizar o
**Factory Pattern**, permitindo isolamento em testes unitários automatizados.

## Restrições Técnicas

As seguintes restrições tecnológicas e de arquitetura MUST ser respeitadas em todo o desenvolvimento do projeto:
- **Tecnologia Principal (Backend)**: Python 3.10+ e FastAPI para o servidor de API local.
- **Tecnologia Principal (Frontend)**: TypeScript, React, Tailwind CSS para estilização, e componentes da shadcn/ui.
- **Arquitetura Modular e Factory Pattern**: Toda a estrutura de código do frontend e do backend MUST ser modular. A instanciação de parsers de arquivo no backend e de serviços de API no frontend MUST utilizar o padrão de fábrica (Factory Pattern) para facilitar testes unitários independentes e extensibilidade.
- **Dockerização (Single Container)**: O frontend e o backend MUST ser empacotados e executados juntos dentro do mesmo container Docker. O backend FastAPI deve servir a build estática do frontend (compilada pelo Vite) ou rodar sob o mesmo processo/container, expondo uma única porta para o usuário final no localhost.
- **Ambiente de Execução**: Execução local independente. O frontend React deve se comunicar com o backend FastAPI via chamadas HTTP locais (localhost). O setup do frontend deve ser inicializado com Vite.

## Processo de Desenvolvimento e Fluxo de Trabalho

- **Foco em Qualidade e Testabilidade**: A lógica do analisador de texto (parser) e endpoints no backend deve possuir cobertura de testes unitários automatizados utilizando pytest.
- **Design Não-Destrutivo**: Qualquer configuração ou parâmetro de filtragem deve ser facilmente resetável no modal de engrenagem, sem afetar os arquivos locais de origem do usuário.
- **Ausência de Placeholders**: Elementos da interface gráfica não devem conter texto genérico "Lorem Ipsum" ou placeholders vazios; usar dados de exemplo realistas durante a exibição inicial.

## Governance

- **Procedimento de Emenda**: Qualquer alteração ou acréscimo de novos princípios nesta Constituição exige a atualização deste arquivo com incremento de versão e justificativa no relatório de impacto.
- **Versão Semântica**: O número da versão da Constituição segue a regra MAJOR.MINOR.PATCH.
- **Conformidade de Código**: Todo plano de implementação (/speckit.plan) e especificação de funcionalidade (/speckit.specify) deve ser validado contra as regras estabelecidas nesta Constituição.

**Version**: 2.1.0 | **Ratified**: 2026-07-02 | **Last Amended**: 2026-07-03
