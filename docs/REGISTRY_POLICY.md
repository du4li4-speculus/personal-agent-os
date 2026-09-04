# Registry Policy v0.1

## Purpose

Define what should be registered in Agent OS registry and prevent confusion between capabilities, reasoning protocols, and system rules.

## Registry Responsibility

Registry contains discoverable and callable capabilities.

A component belongs in registry only when it has:

- a clear purpose
- defined inputs and outputs
- independent execution capability
- versioning requirements
- validation or testing requirements

## Should Be Registered

Examples:

- domain skills
- reusable tools
- execution capabilities

Examples:

- TOEFL writing evaluation
- document generation
- data analysis

## Should Not Be Registered

Do not register:

- cognition protocols
- architecture rules
- global principles
- memory files
- project decisions

These belong to their respective layers.

## Layer Separation

Cognition Layer:
- defines how agents think
- provides reasoning protocols

Skill Layer:
- defines what agents can do
- provides executable capabilities

Registry:
- provides discovery and access to skills

Runtime:
- manages execution and validation
