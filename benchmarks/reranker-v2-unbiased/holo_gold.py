from __future__ import annotations

from typing import Dict, List

# Gold-set design:
# - 32 source families from the canonical holo-agent-tooling specification.
# - 76 semantic intents total: 3 per canonical agent file, 2 per other source.
# - 4 query phrasings per intent (2 pt-BR + 2 en) = 304 queries.
# - Bootstrap group_id is the source family, not the paraphrase, so repeated
#   phrasings never masquerade as independent statistical evidence.

TARGETS = [
    ("library/agents/architecture-auditor/instructions.md", "agents", 3,
     "auditar de forma independente e somente leitura contratos, limites arquiteturais, fluxos, acoplamento, segurança e risco sistêmico",
     "perform an independent read-only audit of contracts, architecture boundaries, flows, coupling, security, and systemic risk",
     "formar a avaliação a partir de evidência objetiva antes de aceitar a conclusão de outro modelo e não editar a implementação",
     "form the assessment from objective evidence before accepting another model's conclusion and do not edit the implementation"),
    ("library/agents/browser/instructions.md", "agents", 3,
     "navegar fontes web e documentação atual para coletar evidência primária e devolver achados curtos com fontes",
     "navigate current web sources and documentation to collect primary evidence and return concise sourced findings",
     "não transformar browsing externo em decisão final de arquitetura ou debugging dependente do repositório",
     "do not turn external browsing into a final architecture or repository-dependent debugging decision"),
    ("library/agents/bug-auditor/instructions.md", "agents", 3,
     "auditar bugs, regressões, invariantes, condições de borda e caminhos de erro com localização e reprodução quando possível",
     "audit bugs, regressions, invariants, boundary conditions, and error paths with locations and reproduction when possible",
     "manter a primeira avaliação independente, somente leitura e baseada em evidência",
     "keep the first assessment independent, read-only, and evidence-based"),
    ("library/agents/data/instructions.md", "agents", 3,
     "investigar SQL, métricas, estatísticas, datasets, notebooks e dashboards de forma reprodutível",
     "investigate SQL, metrics, statistics, datasets, notebooks, and dashboards reproducibly",
     "ser somente leitura e tratar dados ausentes ou inacessíveis como incerteza",
     "remain read-only and treat missing or inaccessible data as uncertainty"),
    ("library/agents/explore/instructions.md", "agents", 3,
     "localizar arquivos, símbolos, referências, dependências e instruções próximas e devolver um mapa compacto de evidências",
     "locate files, symbols, references, dependencies, and nearby instructions and return a compact evidence map",
     "não editar nem tomar a decisão final de arquitetura ou debugging; reduzir poluição de contexto",
     "do not edit or make the final architecture/debugging decision; minimize context pollution"),
    ("library/agents/final-gate/instructions.md", "agents", 3,
     "tomar a decisão final somente leitura a partir de requisitos, verificações, auditorias e risco residual",
     "make the final read-only decision from requirements, verification, audits, and residual risk",
     "falhar fechado quando falta evidência e usar PASS, CORRECT, BLOCK ou INSUFFICIENT_EVIDENCE",
     "fail closed when evidence is missing and use PASS, CORRECT, BLOCK, or INSUFFICIENT_EVIDENCE"),
    ("library/agents/holo/instructions.md", "agents", 3,
     "coordenar o trabalho principal, integrar resultados, escolher capabilities e verificar antes do handoff",
     "coordinate the primary work, integrate results, choose capabilities, and verify before handoff",
     "delegar por papel quando útil, nunca escolher ou substituir silenciosamente o modelo do papel",
     "delegate by role when useful and never choose or silently substitute the model bound to that role"),
    ("library/agents/project-ro/instructions.md", "agents", 3,
     "inspecionar somente o project root nomeado e caminhos explicitamente aprovados, devolvendo evidência e limitações",
     "inspect only the named project root and explicitly approved paths, returning evidence and limitations",
     "não editar arquivos, estado, dependências ou artefatos gerados",
     "do not edit files, state, dependencies, or generated artifacts"),
    ("library/agents/project-rw/instructions.md", "agents", 3,
     "implementar uma mudança explicitamente delegada somente dentro dos caminhos autorizados e verificar o resultado",
     "implement an explicitly delegated change only within authorized paths and verify the result",
     "exigir autorização de escrita e não ampliar para deploy, instalação de dependências ou refactor amplo",
     "require write authorization and do not broaden into deployment, dependency installation, or broad refactoring"),
    ("library/agents/root-cause-specialist/instructions.md", "agents", 3,
     "analisar falhas P0/P1, integrações complexas ou achados contestados construindo uma cadeia causal",
     "analyze P0/P1 failures, complex integrations, or contested findings by building a causal chain",
     "separar sintoma, gatilho, causa raiz, mitigação e evidência falsificadora sem vender remediação especulativa como verificada",
     "separate symptom, trigger, root cause, mitigation, and falsifying evidence without presenting speculative remediation as verified"),
    ("library/agents/shell/instructions.md", "agents", 3,
     "executar comandos limitados e não destrutivos e condensar exit status e saída relevante em evidência",
     "run bounded non-destructive commands and condense exit status and relevant output into evidence",
     "não despejar logs enormes nem converter saída de terminal em causa raiz ou arquitetura sem suporte",
     "do not dump huge logs or turn terminal output into unsupported root-cause or architecture conclusions"),
    ("library/agents/test-engineer/instructions.md", "agents", 3,
     "auditar testes, regressões, cobertura e edge cases e desenhar verificações focadas",
     "audit tests, regressions, coverage, and edge cases and design focused checks",
     "separar testes não rodados, falhas de ambiente e falhas reais; permanecer read-only salvo autorização explícita",
     "separate tests not run, environment failures, and actual failures; remain read-only unless explicitly authorized"),

    ("library/rules/antigravity-2-project-scope.md", "rules", 2,
     "definir o escopo de MCP no Antigravity 2.0 desktop, onde servidores reutilizáveis são globais mas permissões são por Project",
     "define MCP scope in Antigravity 2.0 desktop, where reusable servers are global but permissions are Project-scoped",
     "não confundir desktop 2.0 com CLI/IDE nem simular instalação workspace-local com .agents/mcp_config.json",
     "do not conflate desktop 2.0 with CLI/IDE or simulate workspace-local installation with .agents/mcp_config.json"),
    ("library/rules/canonical-runtime-paths.md", "rules", 2,
     "usar locais canônicos definidos pelo harness para configuração e referências de runtime duráveis para executáveis e scripts",
     "use harness-defined canonical locations for configuration and durable runtime references for executables and scripts",
     "não persistir caminhos temporários, de cache, staging ou downloads e não chamar um path de canônico só porque parece organizado",
     "do not persist temporary, cache, staging, or download paths and do not call a path canonical merely because it looks tidy"),
    ("library/rules/delegation-evidence.md", "rules", 2,
     "definir quando delegar e quais campos de claim, evidence, verification e uncertainty devem voltar no handoff",
     "define when to delegate and which claim, evidence, verification, and uncertainty fields must return in a handoff",
     "preservar contexto independente de auditoria e não chamar vários modelos só para fabricar consenso",
     "preserve independent audit context and do not call multiple models merely to manufacture consensus"),
    ("library/rules/harness-freshness.md", "rules", 2,
     "classificar capabilities de um harness usando a versão instalada, schema atual, documentação recente e smoke test quando barato",
     "classify harness capabilities using the installed version, current schema, recent documentation, and a cheap smoke test when useful",
     "não inferir unsupported por ausência local; distinguir present, missing, broken, unknown, unsupported e not-desired",
     "do not infer unsupported from local absence; distinguish present, missing, broken, unknown, unsupported, and not-desired"),
    ("library/rules/local-harness-application.md", "rules", 2,
     "aplicar a especificação canônica do Holo à configuração live de Kilo, VS Code, Antigravity ou Zed",
     "apply the canonical Holo specification to live Kilo, VS Code, Antigravity, or Zed configuration",
     "seguir pull-first, preservar configuração não-Holo do usuário, fazer backup e validar paths, MCP scope, bindings e autoridade",
     "follow pull-first, preserve non-Holo user configuration, back up changes, and validate paths, MCP scope, bindings, and authority"),
    ("library/rules/mcp-scoping.md", "rules", 2,
     "colocar MCPs específicos do projeto no menor escopo prático e reservar global para capabilities realmente universais",
     "place project-specific MCPs at the narrowest practical scope and reserve global scope for truly universal capabilities",
     "não habilitar todo o capability roster globalmente nem confundir cobertura desejada com autoridade ativa",
     "do not enable the whole capability roster globally or confuse desired coverage with active authority"),
    ("library/rules/session-orchestration.md", "rules", 2,
     "distinguir macro sessões ou worktrees independentes de delegação normal de papéis dentro de uma sessão",
     "distinguish macro independent sessions or worktrees from ordinary role delegation inside a session",
     "não criar sessões extras para simular subagentes nem deixar múltiplos writers atuarem no mesmo worktree",
     "do not create extra sessions to simulate subagents or allow multiple writers on the same worktree"),
    ("library/rules/specification-only.md", "rules", 2,
     "manter Holo Agent Tooling como especificação de arquitetura e não como instalador ou sincronizador universal",
     "keep Holo Agent Tooling as an architecture specification rather than a universal installer or synchronizer",
     "buscar conformance semântica entre harnesses sem exigir os mesmos arquivos, schemas, plugins ou MCPs",
     "target semantic conformance across harnesses without requiring identical files, schemas, plugins, or MCPs"),
    ("library/rules/tool-authority.md", "rules", 2,
     "dar ao coordenador Holo as capabilities aprovadas do projeto enquanto papéis delegados permanecem least-privileged",
     "give the Holo coordinator the project-approved capabilities while delegated roles remain least-privileged",
     "separar disponibilidade, aprovação, escopo MCP, autoridade de delegação e model binding sem deixar subagentes herdarem autoridade ampla",
     "separate availability, approval, MCP scope, delegation authority, and model binding without letting subagents inherit broad authority"),

    ("capabilities/README.md", "capabilities", 2,
     "entender o workflow de inventário de capabilities e a diferença entre roster conceitual e integrações concretas",
     "understand the capability inventory workflow and the difference between the conceptual roster and concrete integrations",
     "buscar paridade semântica em vez de espelhar pacotes e não propagar automaticamente para todos os harnesses",
     "target semantic parity instead of package mirroring and do not automatically propagate to every harness"),
    ("capabilities/hooks.md", "capabilities", 2,
     "entender Hooks como automação de lifecycle do harness",
     "understand Hooks as harness lifecycle automation",
     "considerar seus efeitos sem tratá-los como ferramenta discricionária comum nem duplicar a automação",
     "account for their effects without treating them as an ordinary discretionary tool or duplicating the automation"),
    ("capabilities/integrations.yaml", "capabilities", 2,
     "consultar ou registrar extensões, plugins, MCPs, providers, LSPs, debuggers e outras integrações concretas por harness",
     "consult or record extensions, plugins, MCPs, providers, LSPs, debuggers, and other concrete integrations per harness",
     "registrar implementação, versão, estado de validação e capabilities fornecidas sem confundir pacote com capability portátil",
     "record implementation, version, validation state, and provided capabilities without confusing package identity with portable capability"),
    ("capabilities/mcp-tools.md", "capabilities", 2,
     "selecionar primeiro a capability necessária e depois a MCP ou tool concreta realmente disponível no projeto",
     "select the needed capability first and then the concrete MCP or tool actually available in the project",
     "MCPs e tools não são papéis nem mecanismo geral de seleção de modelo e não justificam registry universal",
     "MCPs and tools are not roles or a general model-selection mechanism and do not justify a universal registry"),
    ("capabilities/roster.yaml", "capabilities", 2,
     "consultar quais capabilities são desejadas e o status de cobertura por harness",
     "consult which capabilities are desired and the coverage status per harness",
     "usar estados como unknown, present, missing, broken, unsupported e not-desired sem exigir o mesmo pacote em todos os harnesses",
     "use states such as unknown, present, missing, broken, unsupported, and not-desired without requiring the same package everywhere"),
    ("capabilities/skills.md", "capabilities", 2,
     "usar Skills como procedimentos reutilizáveis ou conhecimento de domínio selecionados por relevância à tarefa",
     "use Skills as reusable procedures or domain knowledge selected for relevance to the task",
     "Skills são capabilities disponíveis aos papéis, não papéis nem model routers, e não devem ser carregadas só porque estão instaladas",
     "Skills are capabilities available to roles, not roles or model routers, and should not be loaded merely because they are installed"),

    ("library/routing/README.md", "routing", 2,
     "entender os princípios de routing em que o Holo escolhe papéis e o humano mantém autoridade sobre a escolha dos modelos",
     "understand routing principles where Holo selects roles while the human retains authority over model selection",
     "não transformar o coordenador em roteador automático de modelos",
     "do not turn the coordinator into an automatic model router"),
    ("library/routing/model-bindings.yaml", "routing", 2,
     "consultar o model, provider e reasoning binding atual de cada papel canônico",
     "look up the current model, provider, and reasoning binding for each canonical role",
     "o binding é humano e não pode ser silenciosamente substituído ou herdado por conveniência",
     "the binding is human-owned and must not be silently substituted or inherited for convenience"),

    ("AGENTS.md", "docs", 2,
     "consultar as instruções operacionais para agentes trabalhando neste repositório",
     "consult the operating instructions for agents working in this repository",
     "ler as regras do repositório antes de modificar, revisar ou auditar seus arquivos",
     "read repository rules before modifying, reviewing, or auditing its files"),
    ("ARCHITECTURE.md", "docs", 2,
     "entender a arquitetura canônica geral do Holo, seus componentes e invariantes",
     "understand the overall canonical Holo architecture, components, and invariants",
     "usar a visão arquitetural de alto nível antes de decidir se uma mudança preserva o desenho do sistema",
     "use the high-level architecture before deciding whether a change preserves the system design"),
    ("README.md", "docs", 2,
     "obter uma visão geral do propósito, estrutura e uso do Holo Agent Tooling",
     "get an overview of the purpose, structure, and usage of Holo Agent Tooling",
     "encontrar a introdução principal e os caminhos iniciais de leitura do projeto",
     "find the main introduction and initial reading paths for the project"),
]


def _intent_texts(pt_concept: str, en_concept: str, pt_guardrail: str, en_guardrail: str, index: int) -> tuple[str, str]:
    if index == 1:
        return pt_concept, en_concept
    if index == 2:
        return (
            f"{pt_concept}, respeitando esta distinção: {pt_guardrail}",
            f"{en_concept}, while respecting this distinction: {en_guardrail}",
        )
    return (
        f"preciso identificar a fonte canônica para {pt_concept}; um requisito importante é: {pt_guardrail}",
        f"I need the canonical source for this need: {en_concept}; an important constraint is: {en_guardrail}",
    )


def generate_gold_rows() -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    intent_total = 0
    for path, category, intent_count, pt_concept, en_concept, pt_guardrail, en_guardrail in TARGETS:
        family = path
        for intent_idx in range(1, intent_count + 1):
            intent_total += 1
            pt, en = _intent_texts(pt_concept, en_concept, pt_guardrail, en_guardrail, intent_idx)
            variants = [
                ("pt-BR", pt),
                ("pt-BR", f"No Holo, qual fonte canônica devo recuperar para este caso? {pt}"),
                ("en", en),
                ("en", f"In Holo, which canonical source should I retrieve for this case? {en}"),
            ]
            safe = path.replace("/", "__").replace(".", "_")
            for variant_idx, (language, query) in enumerate(variants, start=1):
                rows.append(
                    {
                        "query_id": f"{safe}:i{intent_idx}:v{variant_idx}",
                        "group_id": family,
                        "intent_id": f"{safe}:i{intent_idx}",
                        "query": query,
                        "language": language,
                        "category": category,
                        "relevant_doc_ids": [path],
                    }
                )

    if intent_total != 76:
        raise AssertionError(f"Expected 76 intents, got {intent_total}")
    if len(rows) != 304:
        raise AssertionError(f"Expected 304 queries, got {len(rows)}")
    return rows


if __name__ == "__main__":
    import json
    for row in generate_gold_rows():
        print(json.dumps(row, ensure_ascii=False, sort_keys=True))
