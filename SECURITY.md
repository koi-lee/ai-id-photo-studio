# Security and photo privacy

This repository contains an Agent workflow and local image-processing scripts. The public examples are AI-generated. Do not add private originals, family photos, or derivatives to this repository.

## What the repository can and cannot protect

- GitHub contributors cannot directly read files on your computer by changing code in this public repository.
- Running a modified script locally is different: code runs with the permissions of your user account and may be able to read files and use the network. Review unfamiliar changes before running them. For testing a fork or an unknown change, use a disposable environment that has only public examples and no access to private photo folders.
- `.gitignore` helps prevent accidental staging. It is not a runtime sandbox and can be bypassed with force-add or by changing ignore rules.
- The CI workflow uses `contents: read` and checks out repository contents only. It does not have access to contributors' local photos. Do not add secrets or private photos to CI.
- The image allowlist check catches new non-ignored image files in the working tree and edits to baseline examples. A matching hash is not proof of provenance. A contributor can bypass the check by changing the checker or workflow; review both carefully. Whether a failed CI job blocks merging depends on repository branch-protection settings, which are managed separately.

## Before running or publishing changes

1. Review changed code for local file reads, network requests, subprocesses, install hooks, and new dependencies.
2. Keep personal photos outside the repository. Use the public examples for smoke checks.
3. Before publishing, inspect the exact staged file list and image allowlist check. Unknown-origin images must not be added.
