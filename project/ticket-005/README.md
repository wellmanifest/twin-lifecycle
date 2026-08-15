# Ticket 005: Re-adopt published new-project v0.18.1 governance

- **ID**: ticket-005
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-15

## Goal and scope

Replace the stale `wellmanifest/new-project` 0.16.2 managed governance package
with the final, published `v0.18.1` package at commit
`16f7aea148a7f979e5c5abdfd4bc112224904d36`. This is the upstream revision
that moves managed schema identifiers from `wellmanifest.dev` to
`wellmanifest.com`, so it removes the blocker recorded in pull request #10
without bypassing the adoption lock.

The upgrade is an atomic Goal adoption. Repository-owned Twin contracts remain
as merged by ticket-004; this ticket changes only managed governance artifacts,
their lock, its own evidence, and the root roadmap/index.

## Acceptance criteria

- [x] AC-01: The source commit is the peeled commit of final GitHub release
  `v0.18.1`, and Goal accepts it as a published adoption source.
- [x] AC-02: `goal governance adopt --check` reports the reviewed 13-file
  managed upgrade before writes; `--upgrade` installs the same atomic set.
- [x] AC-03: `.governance/manifest.lock.json` verifies every managed digest and
  records `wellmanifest/new-project` version `0.18.1` at the exact source SHA.
- [x] AC-04: Managed schema identifiers use `wellmanifest.com`; no
  repository-owned Twin contract is changed.
- [x] AC-05: the managed governance gate and Twin lifecycle conformance suite
  pass on the exact implementation head.
- [x] AC-06: publication uses current-head checks plus an independent trusted
  Validator review; the obsolete PR #10 is then closed as superseded rather
  than merged.

## Publication evidence

- Implementation pull request: `wellmanifest/twin-lifecycle#11`.
- Exact reviewed head: `1fd15be28973bbd2e3abe7689039c57f9d5ecda6`.
- Required hosted checks: remote lifecycle run `31857342349` and lifecycle
  conformance run `31857342366`, both successful on the exact head.
- Protected Validator run: `31857368069`, correlation
  `twin-lifecycle-pr-11-ticket-005-1fd15be289`.
- Trusted Validator App approval: review `4942374584`, bound to the exact head
  after two stable reads.
- Integrated default-branch commit:
  `cde5e5e74df9bdf5fbb4eddc016fc120a018fc46`; the implementation branch is
  absent remotely after merge.
- Obsolete pull request `#10` was closed unmerged on 2026-08-15 as superseded
  by `#9` plus the atomic adoption in `#11`. Its exact orphaned remote ref was
  then discarded according to the owner-authored sequence in #10 so the remote
  lifecycle could converge; commit
  `e9eee89ecf6b6f913d74ecccec31487062dbef70` remains recoverable from the
  closed PR and local Git object/ref history.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
