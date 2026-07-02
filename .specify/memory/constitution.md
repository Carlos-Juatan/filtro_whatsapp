<!--
Sync Impact Report:
- Version change: 0.0.0 → 1.0.0
- List of modified principles: None (initial ratification)
- Added sections: Core Principles, Technical Constraints, Development Workflow, Governance
- Removed sections: None
- Templates requiring updates:
  - .specify/templates/plan-template.md: ✅ updated (aligned with local-first and UI principles)
  - .specify/templates/spec-template.md: ✅ updated (aligned with single-user scenarios)
  - .specify/templates/tasks-template.md: ✅ updated (aligned with modular extraction and UI setup)
- Follow-up TODOs: None (all placeholders resolved)
-->

# Extrator e Filtro de P&R Constitution

## Core Principles

### I. Local-First e Usuário Único
O sistema MUST ser executado inteiramente em ambiente local (localhost) sem dependência de serviços em nuvem ou conexões externas de banco de dados. Não deve haver mecanismos de autenticação, login ou gestão de perfis de acesso, visando manter a arquitetura extremamente simples, segura e focada em privacidade.

### II. Processamento Transparente de Arquivos
O processamento de arquivos MUST ser completamente transparente para o usuário. O sistema deve listar visualmente todos os arquivos carregados para processamento, prover um log de execução detalhado em tempo real na tela e destacar claramente os resultados mapeados e a contagem de frequência de perguntas e respostas.

### III. Estética Premium e Micro-animações
A interface web MUST apresentar um design moderno, limpo e atraente. Devemos utilizar esquemas de cores harmoniosos (como tons escuros/sleek dark mode ou paletas HSL customizadas), tipografia moderna (Inter ou Outfit) e micro-animações (como transições de hover nos botões e listas, modais dinâmicos e feedbacks visuais no carregamento de arquivos) para criar uma experiência premium.

### IV. Formatos de Exportação Duplos
Os resultados processados MUST ser exportáveis in dois formatos distintos e bem definidos: um arquivo de texto (.txt) contendo o relatório estruturado legível por humanos (apropriado para Word ou Google Docs) e um arquivo estruturado JSON contendo a lista completa de perguntas e respostas com seus respectivos metadados para consumo programático.

### V. Mecanismo de Extração Modular
O algoritmo de extração, filtragem e contabilização de perguntas e respostas MUST ser desenvolvido de forma desacoplada da interface do usuário (DOM). Isso permite que a lógica de processamento seja testada de forma isolada através de testes unitários automatizados, garantindo a corretude e a robustez do processamento de texto.

## Restrições Técnicas

As seguintes restrições tecnológicas e de arquitetura MUST ser respeitadas em todo o desenvolvimento do projeto:
- **Tecnologia Principal**: Frontend em HTML5 semântico, JavaScript moderno (ES6+) e CSS3 nativo para estilização.
- **Ambiente de Execução**: Execução local no navegador web. Caso seja necessária uma estrutura de build ou servidor de desenvolvimento local, utilizar Vite pela rapidez e simplicidade.
- **Sem Bibliotecas de Estilização Complexas**: Evitar frameworks CSS invasivos como TailwindCSS a menos que solicitado pelo usuário, priorizando CSS puro (Vanilla CSS) com variáveis (Custom Properties) para consistência estética.

## Processo de Desenvolvimento e Fluxo de Trabalho

- **Foco em Qualidade e Testabilidade**: A lógica do analisador de texto (parser) deve possuir cobertura de testes unitários para múltiplos formatos de arquivo brutos de entrada.
- **Design Não-Destrutivo**: Qualquer configuração ou parâmetro de filtragem deve ser facilmente resetável no modal de engrenagem, sem afetar os arquivos locais de origem do usuário.
- **Ausência de Placeholders**: Elementos da interface gráfica não devem conter texto genérico "Lorem Ipsum" ou placeholders vazios; usar dados de exemplo realistas durante a exibição inicial.

## Governance

- **Procedimento de Emenda**: Qualquer alteração ou acréscimo de novos princípios nesta Constituição exige a atualização deste arquivo com incremento de versão e justificativa no relatório de impacto.
- **Versão Semântica**: O número da versão da Constituição segue a regra MAJOR.MINOR.PATCH.
- **Conformidade de Código**: Todo plano de implementação (/speckit.plan) e especificação de funcionalidade (/speckit.specify) deve ser validado contra as regras estabelecidas nesta Constituição.

**Version**: 1.0.0 | **Ratified**: 2026-07-02 | **Last Amended**: 2026-07-02
