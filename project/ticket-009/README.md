# Ticket 009: Adopt new-project standard 0.18.5

- **ID**: ticket-009
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Utworzono**: 2026-08-23

## Cel i Zakres

To repozytorium było na standardzie `0.18.1` i miało zainstalowany walidator
governance, którego CI nigdy nie uruchamiało. Nie miało też żadnego pliku
kontraktu poza `AGENTS.md`, więc Claude Code, Gemini, Cursor i aider nie
ładowały żadnych reguł, a `core.hooksPath` nie był ustawiony — commit poza
ticketem przechodził bez przeszkód.

Adopcja `0.18.5` jest jedną niepodzielną transakcją wykonaną przez
`create_adoption_lock.py`: 28 plików, każdy związany digestem w
`.governance/manifest.lock.json`. Przynosi kontrakt host-agnostyczny
(`CLAUDE.md`, `GEMINI.md`, regułę Cursora, `.githooks/pre-commit`,
`.governance/agent-hosts.json` i jego walidator) oraz job
`governance / enforce`, który uruchamia bramę w CI tego repozytorium.

Dwa pliki są własnością tego repozytorium, nie standardu, i musiały zostać
napisane ręcznie po adopcji:

- `.governance/required-checks.json` deklarowało `test` i `windows-governance`
  z `.github/workflows/ci.yml` — workflow, którego tu nie ma. Deklaracja
  pochodziła z huba i była nieprawdziwa. Teraz wymienia trzy checki faktycznie
  publikowane przez to repozytorium.
- `coordination.workstreams.governance.ownedPaths` w `.governance/manifest.json`
  nie obejmowało nowych artefaktów kontraktu, więc `GOV-WORKSTREAM-003`
  odrzucał ticket. Workstream `governance` przejmuje je jawnie.

## Kryteria Odbioru (Acceptance Criteria)

- [x] AC-01: `python3 .governance/agent_host_check.py --root .` →
  `GOV-AGENT-HOST-PASS` po `./scripts/install-agent-hosts.sh`.
- [x] AC-02: `./project/governance-check.sh --actor agent` → `GOV-PASS`, każdy
  managed digest zgodny z nowym lockiem.
- [x] AC-03: `python3 standard/conformance.py --all` — domenowy standard twin
  lifecycle nietknięty przez adopcję.

## Ryzyka i Uwagi

- Risk 1: `governance / enforce` nie jest jeszcze wymaganym checkiem w
  rulesecie tego repozytorium. Ruleset żyje poza repozytorium; to osobna
  decyzja człowieka. Do tego czasu job jest sygnałem, nie blokadą.
- Risk 2: hook odrzuca odtąd commity niezwiązane z ticketem `IN_PROGRESS`.
  Wymaga to `./scripts/install-agent-hosts.sh` raz na klon; sama adopcja
  dostarcza pliki, ale nie ustawia `core.hooksPath` w cudzych klonach.

## Uczestnicy

- Human participant: unresolved; `user-*` is created only by its human owner
  or a trusted intake boundary.
- Agent participant: `ai-claude.md`

## Granica katalogu

Ten katalog przechowuje governance, decyzje, logi i dowody. Kod wykonywalny,
skrypty badawcze i testy należą do zwykłych katalogów źródłowych repozytorium,
nie do `project/ticket-009/`.
