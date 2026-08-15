# Ticket 004: Point schema identifiers at the live host

- **ID**: ticket-004
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-14

## Goal and scope

A local commit repointed every schema identifier from `wellmanifest.dev` to
`wellmanifest.com` so the packs resolve on the live host. The intent is right
and this ticket takes it — but only for the half of the change this repository
owns.

The other half edited five files the adoption lock hashes
(`diagnostics.schema.json`, `governance_check.py`, `manifest.base.json`,
`manifest.schema.json`, `remediation-intent.schema.json`). All five stop
matching `manifest.lock.json`, which would leave the repository claiming an
adoption it no longer matches. A managed-file rename belongs upstream in
`wellmanifest/new-project`, followed by re-adoption through the generator.

Changing the schema `$id` and the blueprint `definitionUri` moves their
canonical digests, so the pinned schema digest is re-pinned in the same change.

## Acceptance criteria

- [x] AC-01: `standard/conformance.py --all` passes with the re-pinned digest:
  4 canonical documents accepted, 30 adversarial mutations rejected.
- [x] AC-02: Every file in `.governance/manifest.lock.json` still hashes to its
  recorded value.
- [x] AC-03: The managed gate passes with the change resolving to exactly one
  integration ticket.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-claude.md](ai-claude.md)
- Closure participant: [ai-codex.md](ai-codex.md)

## Publication evidence

- Implementation pull request: `wellmanifest/twin-lifecycle#9`.
- Exact reviewed head: `ebc109db6cff9dbd371684d8c37db3eaa33759c4`.
- Hosted checks on the exact head: lifecycle conformance run `31823064124`
  and remote lifecycle run `31823064199`, both successful.
- Trusted Validator App approval: review `4940019179`, ticket `ticket-004`,
  correlation `twin-lifecycle-pr-9-ticket-004-ebc109db6c`, deterministic
  authority.
- Integrated default-branch commit:
  `20ba9508392ff91f97a68e2879b1073eff1119be`, merged at
  `2026-08-14T18:10:10Z`; the implementation branch is absent remotely.
- The separately managed host identifiers were later delivered through the
  published-SHA governance transaction in ticket-005 / PR #11, preserving the
  boundary explicitly excluded by this ticket.
