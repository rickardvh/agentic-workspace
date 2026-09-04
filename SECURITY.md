# Security policy

Security fixes are made on the current 1.x branch. Report vulnerabilities with
[GitHub private vulnerability reporting](https://github.com/rickardvh/agentic-workspace/security/advisories/new).

Agentic Workspace is not a sandbox. Module entry points and validation commands
execute trusted code with the caller's permissions. Typed operation schemas,
effect declarations, currentness checks, and bounded removal prevent accidental
authority widening; they do not make an untrusted repository safe to execute.
