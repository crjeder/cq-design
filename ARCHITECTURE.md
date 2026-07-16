``` mermaid
---
config:
  layout: dagre
---
flowchart TB
    A["`**Plan:** <br> LLM describes the mechanical strategy`"] --> B["`**Draft:** <br>LLM writes the CadQuery code.`"]
    B -- generated code --> C["`**Audit:** <br>Programm eviews for 3D printing failure points`"]
    C -- identifies quality issues --> E{"`**Verification**<br>Clean?`"}
    D["`**Refine:** <br>LLM applies the fixes`"] -- refined code --> C
    E -- "No - issues found" --> D
    E -- "Yes - clean" --> K["`**Audit**<br>LLM audits if the plan is implemented`"]
    K --> H{"`Implementation<br> according to <br>**Plan**?`"}
    H -- "No - deviates from plan" --> D
    H -- Plan implemented --> I["Customer Review"]
    F["Programm optimizes print orientation"] --> G["✓ Final Code"]
    I --> J{"Approved"}
    J -- Yes --> F
    J -- No --> D


    style A stroke:#818cf8,fill:#eef2ff
    style B stroke:#818cf8,fill:#eef2ff
    style C stroke:#AA00FF,fill:#E1BEE7
    style E stroke:#f87171,fill:#fef2f2
    style D stroke:#818cf8,fill:#eef2ff
    style K stroke:#818cf8,fill:#eef2ff
    style H stroke:#f87171,fill:#fef2f2
    style I fill:#FFE0B2,stroke:#FF6D00
    style F stroke:#AA00FF,fill:#E1BEE7
    style G stroke:#4ade80,fill:#f0fdf4
    style J stroke:#f87171,fill:#fef2f2
```
# Plan 
- Interview user intent
- Web search
- measure dimensions in .stl, .step ...

# Agents
- Plan
- Draft
- Audit
- Refine
