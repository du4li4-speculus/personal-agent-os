# Agent OS Architecture Boundaries v0.1

## Purpose
Define responsibilities and boundaries between Agent OS, projects, skills, memory, and runtime.

## Layers

### Agent OS
Responsible for:
- reasoning protocols
- expansion methods
- critique methods
- memory rules
- agent coordination

Not responsible for:
- domain-specific knowledge
- project execution details


### Project Layer
Examples:
- TOEFL-Agent-OS
- APAL
- Furry

Responsible for:
- project goals
- project decisions
- project-specific workflows


### Skill Layer
Responsible for:
- specific capabilities
- domain execution
- reusable tools

Examples:
- TOEFL writing evaluation
- document generation


### Memory Layer
Contains:
- global principles
- project history
- failure lessons

Must not mix unrelated domains.


## Extension Rule

Before adding any new component, decide:

1. Which layer does it belong to?
2. Is it reusable across projects?
3. Does it represent:
   - knowledge
   - workflow
   - memory
   - tool
