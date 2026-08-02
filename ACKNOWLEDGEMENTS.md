# Acknowledgements

RepoLoop is an independent implementation built with gratitude for the open-source agent tooling that preceded it.

## Primary architectural inspiration

[Q00/Ouroboros](https://github.com/Q00/ouroboros), created by Q00, is the original specification-first workflow engine that inspired several RepoLoop design choices:

- explicit specification contracts;
- append-only execution evidence;
- evaluation outside the worker context;
- replaceable coding-runtime adapters;
- resumable workflow semantics;
- bounded, policy-aware agent execution.

RepoLoop is not a fork of Ouroboros and does not claim Ouroboros source code as its own. RepoLoop applies those architectural ideas to a narrower domain: compiling repositories into governed capsules and running repository-specific loops. Ouroboros remains the credited origin for the reused conceptual substrate.

## Open-source ecosystem

- [Textual](https://github.com/Textualize/textual) powers the terminal interface.
- [LangGraph](https://github.com/langchain-ai/langgraph) informs the planned checkpointed state-machine runtime; it is not yet a runtime dependency.
- [Model Context Protocol](https://modelcontextprotocol.io/) informs the planned capability-discovery boundary; MCP routing is not yet implemented in this release.

Each project retains its own copyright, trademarks, and license. Inclusion here does not imply endorsement or affiliation.
