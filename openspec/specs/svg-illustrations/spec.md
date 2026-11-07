# Svg Illustrations

## Purpose

TBD

## Requirements

### Requirement: Diagrams in shipped prose are SVG files

Diagrams and layout illustrations in `README.md`, `SKILL.md`, `skill/`, `reference/`, `ARCHITECTURE.md` and `documentation/` SHALL be SVG files, referenced by an image link with a text alt: under `reference/img/` for shipped prose, under `documentation/img/` for development docs. Mermaid diagrams are text and stay. Fenced ASCII-art diagrams SHALL NOT remain, except file/directory trees and tables.

#### Scenario: No ASCII diagram remains
- **WHEN** the shipped markdown is scanned for fenced blocks that draw boxes or arrows
- **THEN** none are found outside file trees

#### Scenario: Referenced SVG exists
- **WHEN** a markdown file references `reference/img/<name>.svg`
- **THEN** the file exists, parses as XML, and has a root `svg` element

### Requirement: LLM-read prompts keep a text description

A diagram in `prompts/*.md` SHALL be replaced by a prose description of what it conveyed, because prompts are rendered to text. The SVG MAY be added to the human-facing docs.

#### Scenario: Prompt diagram replaced
- **WHEN** a former ASCII diagram in a prompt carried information
- **THEN** the prompt states that information in prose and contains no box-drawing art

### Requirement: SVG files ship with a copy install

An SVG referenced from shipped prose SHALL live inside an allowlisted installer entry (`reference/img/`).

#### Scenario: Copy install
- **WHEN** the skill is copied by the installer
- **THEN** every SVG referenced from shipped markdown is present in the destination
