# Graph Report - .  (2026-04-18)

## Corpus Check
- 171 files · ~139,358 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 18 nodes · 25 edges · 4 communities detected
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.79)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]

## God Nodes (most connected - your core abstractions)
1. `MCP Tools: code-review-graph (CLAUDE.md)` - 12 edges
2. `Knowledge Graph (code-review-graph)` - 4 edges
3. `Code Review Workflow` - 4 edges
4. `Impact Analysis / Blast Radius` - 3 edges
5. `Architecture Exploration` - 3 edges
6. `MCP Tools: code-review-graph (GEMINI.md)` - 2 edges
7. `MCP Tools: code-review-graph (AGENTS.md)` - 2 edges
8. `detect_changes` - 2 edges
9. `get_review_context` - 2 edges
10. `get_impact_radius` - 2 edges

## Surprising Connections (you probably didn't know these)
- `MCP Tools: code-review-graph (GEMINI.md)` --semantically_similar_to--> `MCP Tools: code-review-graph (CLAUDE.md)`  [EXTRACTED] [semantically similar]
  GEMINI.md → CLAUDE.md
- `MCP Tools: code-review-graph (AGENTS.md)` --semantically_similar_to--> `MCP Tools: code-review-graph (CLAUDE.md)`  [EXTRACTED] [semantically similar]
  AGENTS.md → CLAUDE.md
- `MCP Tools: code-review-graph (GEMINI.md)` --semantically_similar_to--> `MCP Tools: code-review-graph (AGENTS.md)`  [EXTRACTED] [semantically similar]
  GEMINI.md → AGENTS.md

## Communities

### Community 0 - "Community 0"
Cohesion: 0.43
Nodes (7): MCP Tools: code-review-graph (AGENTS.md), MCP Tools: code-review-graph (CLAUDE.md), Architecture Exploration, MCP Tools: code-review-graph (GEMINI.md), get_architecture_overview, list_communities, semantic_search_nodes

### Community 1 - "Community 1"
Cohesion: 0.5
Nodes (4): Graph Auto-update on File Changes (via hooks), Knowledge Graph (code-review-graph), Rationale: Use graph tools before Grep/Glob/Read — faster, cheaper, provides structural context, refactor_tool

### Community 2 - "Community 2"
Cohesion: 0.5
Nodes (4): Code Review Workflow, detect_changes, get_review_context, query_graph

### Community 3 - "Community 3"
Cohesion: 0.67
Nodes (3): Impact Analysis / Blast Radius, get_affected_flows, get_impact_radius

## Knowledge Gaps
- **2 isolated node(s):** `Rationale: Use graph tools before Grep/Glob/Read — faster, cheaper, provides structural context`, `Graph Auto-update on File Changes (via hooks)`
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MCP Tools: code-review-graph (CLAUDE.md)` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`?**
  _High betweenness centrality (0.820) - this node is a cross-community bridge._
- **Why does `Knowledge Graph (code-review-graph)` connect `Community 1` to `Community 0`?**
  _High betweenness centrality (0.228) - this node is a cross-community bridge._
- **Why does `get_impact_radius` connect `Community 3` to `Community 0`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Code Review Workflow` (e.g. with `query_graph` and `Impact Analysis / Blast Radius`) actually correct?**
  _`Code Review Workflow` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Rationale: Use graph tools before Grep/Glob/Read — faster, cheaper, provides structural context`, `Graph Auto-update on File Changes (via hooks)` to the rest of the system?**
  _2 weakly-connected nodes found - possible documentation gaps or missing edges._