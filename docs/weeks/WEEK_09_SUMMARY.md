# WEEK 9 — FINAL TOOL-CALLING ARCHITECTURE

                              ┌───────────────────────┐
                              │       FRONTEND        │
                              │   Chat UI / Request   │
                              └───────────┬───────────┘
                                          │
                                          │ User Message
                                          ▼
                              ┌───────────────────────┐
                              │       CHAT API        │
                              │      router.py        │
                              └───────────┬───────────┘
                                          │
                                          │ JWT Authenticated
                                          │ + conversation ownership
                                          ▼
                              ┌───────────────────────┐
                              │      CHAT SERVICE     │
                              │    chat_service.py    │
                              └───────────┬───────────┘
                                          │
                                          │ query
                                          │ user_id
                                          │ conversation_id
                                          │ message history
                                          ▼
                              ┌───────────────────────┐
                              │       LANGGRAPH       │
                              │      graph.py         │
                              └───────────┬───────────┘
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │       AGENT NODE      │
                              │       agent.py        │
                              │                       │
                              │  Gemini Decision      │
                              └───────────┬───────────┘
                                          │
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │        GEMINI         │
                              │   Tool Definitions    │
                              │                       │
                              │  • search_documents  │
                              │  • get_workspace_stats│
                              │  • web_search        │
                              └───────────┬───────────┘
                                          │
                            "What should I do?"
                                          │
                         ┌────────────────┴────────────────┐
                         │                                 │
                         ▼                                 ▼
                  ┌──────────────┐                 ┌────────────────┐
                  │   NO TOOL    │                 │   TOOL CALL    │
                  │   REQUIRED   │                 │   REQUIRED     │
                  └──────┬───────┘                 └───────┬────────┘
                         │                                  │
                         │                                  │
                         ▼                                  ▼
                  ┌──────────────┐                 ┌────────────────┐
                  │    END       │                 │   GRAPH STATE  │
                  │              │                 │  tool_calls    │
                  └──────┬───────┘                 └───────┬────────┘
                         │                                  │
                         │                                  ▼
                         │                         ┌────────────────┐
                         │                         │  CONDITIONAL   │
                         │                         │     ROUTING    │
                         │                         │  routing.py    │
                         │                         └───────┬────────┘
                         │                                 │
                         │                         tool_calls exists
                         │                                 │
                         │                                 ▼
                         │                         ┌────────────────┐
                         │                         │   TOOL NODE    │
                         │                         │    tools.py    │
                         │                         └───────┬────────┘
                         │                                 │
                         │                                 │ Execute
                         │                                 ▼
                         │                         ┌────────────────┐
                         │                         │ TOOL REGISTRY  │
                         │                         │   registry.py  │
                         │                         └───────┬────────┘
                         │                                 │
                         │                    ┌────────────┼────────────┐
                         │                    │            │            │
                         │                    ▼            ▼            ▼
                         │             ┌────────────┐ ┌───────────┐ ┌───────────┐
                         │             │  DOCUMENT  │ │ WORKSPACE │ │   WEB     │
                         │             │   SEARCH   │ │  STATS    │ │  SEARCH   │
                         │             │   TOOL     │ │   TOOL    │ │   TOOL    │
                         │             └─────┬──────┘ └─────┬─────┘ └─────┬─────┘
                         │                   │              │             │
                         │                   │              │             │
                         │                   ▼              ▼             ▼
                         │             ┌────────────┐ ┌───────────┐ ┌───────────┐
                         │             │ RAG SERVICE│ │ REPOSITORY │ │   TAVILY  │
                         │             │            │ │    LAYER   │ │   API     │
                         │             └─────┬──────┘ └─────┬─────┘ └───────────┘
                         │                   │              │
                         │                   ▼              ▼
                         │             ┌────────────┐ ┌──────────────┐
                         │             │   HYBRID   │ │  PostgreSQL  │
                         │             │ RETRIEVER  │ │   Database   │
                         │             └─────┬──────┘ └──────────────┘
                         │                   │
                         │            ┌──────┴──────┐
                         │            │             │
                         │            ▼             ▼
                         │     ┌────────────┐ ┌────────────┐
                         │     │  Semantic  │ │    BM25    │
                         │     │  Retriever │ │  Retriever │
                         │     └─────┬──────┘ └─────┬──────┘
                         │           │              │
                         │           └──────┬───────┘
                         │                  │
                         │                  ▼
                         │           ┌──────────────┐
                         │           │ CROSS ENCODER│
                         │           │   RERANKER   │
                         │           └──────┬───────┘
                         │                  │
                         │                  ▼
                         │           ┌──────────────┐
                         │           │  RETRIEVED   │
                         │           │    CHUNKS    │
                         │           └──────┬───────┘
                         │                  │
                         │                  │
                         │                  │
                         │     ┌────────────┘
                         │     │
                         │     ▼
                         │ ┌────────────────┐
                         │ │  TOOL RESULT   │
                         │ │                │
                         │ │ Structured     │
                         │ │ Pydantic data │
                         │ └───────┬────────┘
                         │         │
                         │         ▼
                         │ ┌────────────────┐
                         │ │  GRAPH STATE   │
                         │ │ tool_results   │
                         │ └───────┬────────┘
                         │         │
                         │         ▼
                         │ ┌────────────────┐
                         │ │     AGENT      │
                         │ │      NODE      │
                         │ └───────┬────────┘
                         │         │
                         │         │ Tool result added
                         │         │ to Gemini context
                         │         ▼
                         │ ┌────────────────┐
                         │ │     GEMINI     │
                         │ │                │
                         │ │ Understands    │
                         │ │ tool result    │
                         │ └───────┬────────┘
                         │         │
                         │         │
                         │         ▼
                         │ ┌────────────────┐
                         │ │ FINAL NATURAL  │
                         │ │    LANGUAGE    │
                         │ │    ANSWER      │
                         │ └───────┬────────┘
                         │         │
                         └─────────┤
                                   ▼
                         ┌───────────────────────┐
                         │      CHAT SERVICE     │
                         │                       │
                         │ Save assistant reply │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │       CHAT API        │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │       FRONTEND        │
                         │                       │
                         │ Display final answer │
                         └───────────────────────┘


# Tool-specific flows

 # 1. Document Search

                    Gemini
                    ↓
                    search_documents(query, top_k)
                    ↓
                    Tool Node
                    ↓
                    Tool Registry
                    ↓
                    DocumentSearchTool
                    ↓
                    RAGService
                    ↓
                    HybridRetriever
                    ├── SemanticRetriever
                    │      ↓
                    │   Embeddings
                    │      ↓
                    │   Vector Search
                    │
                    └── BM25Retriever
                         ↓
                         Keyword Search

                    ↓
                    Merge Results
                    ↓
                    CrossEncoderReranker
                    ↓
                    Top Relevant Chunks
                    ↓
                    DocumentSearchOutput
                    ↓
                    Tool Node
                    ↓
                    Agent
                    ↓
                    Gemini
                    ↓
                    Final Answer




 # 2. Workspace Statistics

                    Gemini
                    ↓
                    get_workspace_stats()
                    ↓
                    Tool Node
                    ↓
                    Tool Registry
                    ↓
                    WorkspaceStatsTool
                    ↓
                    Repositories
                    ├── DocumentRepository
                    ├── DocumentChunkRepository
                    ├── ConversationRepository
                    └── MessageRepository
                    ↓
                    User-scoped PostgreSQL queries
                    ↓
                    WorkspaceStatsOutput
                    ↓
                    Tool Node
                    ↓
                    Agent
                    ↓
                    Gemini
                    ↓
                    Final Natural Language Answer

 # 3. Web Search

                    Gemini
                    ↓
                    web_search(query, max_results)
                    ↓
                    Tool Node
                    ↓
                    Tool Registry
                    ↓
                    WebSearchTool
                    ↓
                    WebSearchService
                    ↓
                    Tavily API
                    ↓
                    Web Results
                    ↓
                    WebSearchOutput
                    ↓
                    Tool Node
                    ↓
                    Agent
                    ↓
                    Gemini
                    ↓
                    Final Natural Language Answer

# Week 9 Core Responsibility Separation

                    ┌─────────────────────────────────────────────────────┐
                    │                    GEMINI                           │
                    │                                                     │
                    │ Decides WHAT action should be taken                 │
                    │                                                     │
                    │ • Answer directly                                   │
                    │ • Call search_documents                             │
                    │ • Call get_workspace_stats                          │
                    │ • Call web_search                                   │
                    └────────────────────────┬────────────────────────────┘
                                             │
                                             ▼
                    ┌─────────────────────────────────────────────────────┐
                    │                  LANGGRAPH                          │
                    │                                                     │
                    │ Controls the WORKFLOW                               │
                    │                                                     │
                    │ • Agent                                             │
                    │ • Conditional routing                               │
                    │ • Tool Node                                         │
                    │ • State management                                  │
                    │ • Agent ↔ Tool loop                                 │
                    └────────────────────────┬────────────────────────────┘
                                             │
                                             ▼
                    ┌─────────────────────────────────────────────────────┐
                    │                 TOOL REGISTRY                       │
                    │                                                     │
                    │ Resolves WHICH implementation to execute            │
                    └────────────────────────┬────────────────────────────┘
                                             │
                              ┌───────────┼────────────┐
                              ▼           ▼            ▼
                         Document Tool  Stats Tool   Web Tool
                              │           │            │
                              ▼           ▼            ▼
                              RAG       PostgreSQL    Tavily


# Final Week 9 Architecture in One Line

     User → Chat API → ChatService → LangGraph Agent → Gemini → Tool Decision → Conditional Router → Tool Node → Tool Registry → Selected Tool → Tool Result → Graph State → Agent → Gemini → Final Answer → ChatService → Frontend

# Most important architectural principle

     Gemini = DECISION MAKER
     LangGraph = WORKFLOW ORCHESTRATOR
     Tool Node = EXECUTOR
     Tool Registry = TOOL RESOLVER
     Tools = CAPABILITIES
     Services = BUSINESS LOGIC
     Repositories = DATA ACCESS




# Week 9 — Tool Calling & LangGraph Integration

## 1. Designed the Tool Architecture

We first designed a reusable tool architecture for the AI Knowledge Assistant.

The architecture separates:

* **Tool definitions**
* **Tool input/output schemas**
* **Tool implementations**
* **Tool registry**
* **Tool execution**
* **LLM tool selection**
* **LangGraph orchestration**

The overall architecture became:

```text
User
 ↓
ChatService
 ↓
LangGraph
 ↓
Agent
 ↓
Gemini
 ↓
Tool Decision
 ├── No Tool → Final Answer
 │
 └── Tool Required
       ↓
    Tool Node
       ↓
   Tool Registry
       ↓
   Selected Tool
```

---

## 2. Implemented the Base Tool Architecture

Created a reusable `BaseTool` abstraction.

It provides a common interface for all tools:

```text
BaseTool
 ├── name
 ├── description
 ├── input_schema
 ├── output_schema
 ├── validate_input()
 ├── validate_output()
 └── execute()
```

This ensures that every tool follows the same structure and uses validated Pydantic input/output models.

---

## 3. Implemented Tool Input/Output Schemas

Created structured Pydantic schemas for the tools.

Implemented schemas for:

```text
SearchDocumentsInput
SearchDocumentsOutput

WorkspaceStatsInput
WorkspaceStatsOutput

WebSearchInput
WebSearchOutput
```

The schemas define what arguments the LLM can provide and what structured data each tool returns.

Extra fields were also forbidden to make tool input validation strict.

---

# 4. Implemented Document Search Tool

Implemented:

```text
search_documents
```

The tool allows the Agent to search the authenticated user's uploaded knowledge base.

Architecture:

```text
DocumentSearchTool
 ↓
RAGService
 ↓
HybridRetriever
 ├── Semantic Search
 └── BM25 Search
 ↓
Cross Encoder Reranker
 ↓
Retrieved Chunks
```

The tool returns structured information including:

```text
document
chunk_index
content
score
```

### Important security implementation

The document search was made **user-scoped**.

The authenticated `user_id` is propagated through:

```text
Agent
 ↓
Tool
 ↓
RAGService
 ↓
Retriever
 ↓
Repository
```

The repository filters documents/chunks by the authenticated user.

This prevents one user from retrieving another user's documents.

---

# 5. Implemented Workspace Statistics Tool

Implemented:

```text
get_workspace_stats
```

This tool provides statistics about the authenticated user's workspace.

It returns:

```text
documents
chunks
conversations
messages
```

The required repository-level count operations were implemented using user-scoped database queries.

Architecture:

```text
WorkspaceStatsTool
 ↓
Repositories
 ├── DocumentRepository
 ├── DocumentChunkRepository
 ├── ConversationRepository
 └── MessageRepository
 ↓
Structured Statistics
```

The tool does **not** require the LLM to provide a `user_id`; the authenticated user is injected by the application.

---

# 6. Implemented Web Search Tool

Selected **Tavily** as the external web-search provider.

Implemented:

```text
web_search
```

Architecture:

```text
WebSearchTool
 ↓
WebSearchService
 ↓
Tavily
 ↓
Web Results
```

The results are normalized into a consistent structure:

```text
title
url
snippet
source
```

The tool also validates:

* non-empty queries
* maximum result count
* structured output

---

# 7. Implemented the Tool Registry

Created a central:

```text
ToolRegistry
```

The registry is responsible for managing and executing tools.

It supports:

```text
register()
get_tool()
list_tools()
get_all_tools()
execute()
```

The registered tools are:

```text
search_documents
get_workspace_stats
web_search
```

Architecture:

```text
                 ToolRegistry
                      │
          ┌───────────┼───────────┐
          ↓           ↓           ↓
 search_documents  workspace   web_search
                    _stats
```

Duplicate tool registration and unknown-tool execution are validated.

---

# 8. Created the Tool Registry Factory

Created a centralized factory responsible for constructing the complete tool environment for an authenticated user.

It wires together:

```text
Repositories
RAG Components
RAGService
WebSearchService
Tools
ToolRegistry
```

This avoids manually constructing all dependencies wherever tools are required.

The factory creates a **user-scoped ToolRegistry**.

---

# 9. Implemented Gemini Function Calling

Implemented manual Gemini function/tool calling using the newer `google-genai` SDK.

Gemini receives the available tool definitions and decides whether a tool is required.

Conceptually:

```text
User Query
    ↓
Gemini
    ↓
Should I use a tool?
    ├── No
    └── Yes → Function Call
```

Automatic function calling was disabled so that **our application controls the tool execution flow**.

Gemini only decides:

```text
which tool
+
what arguments
```

It does not directly execute our Python tools.

---

# 10. Implemented Tool Calling Service

Created/refactored `ToolCallingService` to act as the Gemini protocol adapter.

It handles:

* building Gemini tool declarations
* sending tool definitions to Gemini
* calling Gemini
* extracting function calls
* extracting final responses
* preserving Gemini model content
* creating tool-response content
* serializing structured tool results

The service was intentionally separated from actual tool execution.

---

# 11. Tested Tool Calling Independently

Before integrating with LangGraph, we tested the tool-calling mechanism separately.

Verified that Gemini could:

```text
Answer normally
        ↓
Detect tool requirement
        ↓
Generate function call
        ↓
Execute selected tool
        ↓
Receive result
        ↓
Generate final answer
```

Tested scenarios included:

* normal conversational question
* workspace statistics
* document search
* no-tool questions

---

# 12. Integrated Tool Calling with LangGraph

The next step was to move the orchestration into LangGraph.

Previously, the tool loop was handled inside `ToolCallingService`.

We changed the architecture so that:

> **LangGraph controls the workflow, while Gemini controls the tool decision.**

The new graph became:

```text
START
  ↓
Agent
  ↓
Gemini
  ↓
Tool Required?
 ├───────────────┐
 No              Yes
 ↓                ↓
END            Tool Node
                  ↓
             Tool Registry
                  ↓
                Tool
                  ↓
             Tool Result
                  ↓
                Agent
                  ↓
               Gemini
                  ↓
              Final Answer
                  ↓
                 END
```

---

# 13. Extended LangGraph State

Extended `ChatState` to carry tool-calling information.

Added:

```text
user_id
conversation_id
query
messages
tool_calls
tool_results
gemini_contents
response
```

The important additions were:

### `tool_calls`

Stores the tool requested by Gemini.

```text
tool name
+
arguments
```

### `tool_results`

Stores the result returned by the executed tool.

### `gemini_contents`

Preserves the Gemini conversation/tool-call context so Gemini can understand the tool result when it is called again.

---

# 14. Implemented the Agent Node

Created:

```text
Agent Node
```

Its responsibility is to communicate with Gemini and determine the next action.

The Agent:

1. receives the user query
2. provides Gemini with the available tool definitions
3. calls Gemini
4. checks whether Gemini requested a tool
5. stores the tool call in graph state
6. or stores the final response

The Agent itself does **not execute tools**.

---

# 15. Implemented the Tool Node

Created:

```text
Tool Node
```

Its responsibility is to execute the tools requested by Gemini.

Flow:

```text
Tool Call
   ↓
Tool Node
   ↓
Tool Registry
   ↓
Find Tool
   ↓
Validate Arguments
   ↓
Execute Tool
   ↓
Structured Result
   ↓
Store in Graph State
```

This keeps tool execution separate from the Agent/LLM logic.

---

# 16. Implemented Conditional Routing

Created conditional routing based on the structured `tool_calls` state.

The routing logic is:

```text
Agent
 ↓
tool_calls exists?
 ├── Yes → Tool Node
 └── No  → END
```

There is **no keyword-based routing**.

Gemini makes the tool decision, and LangGraph routes according to Gemini's structured function call.

---

# 17. Implemented the Tool Result → LLM → Final Answer Loop

Completed the final tool-calling loop.

The tool result is converted into Gemini-compatible function-response content and added to the model's context.

Flow:

```text
User
 ↓
Agent
 ↓
Gemini
 ↓
Tool Call
 ↓
Tool Node
 ↓
Tool Registry
 ↓
Tool Execution
 ↓
Structured Tool Result
 ↓
Gemini Context
 ↓
Agent
 ↓
Gemini
 ↓
Natural Language Final Answer
```

This prevents raw tool JSON from being shown directly to the user.

For example:

```text
Tool result:

{
  "documents": 12,
  "chunks": 1847
}
```

becomes a natural response such as:

```text
You currently have 12 documents containing
1,847 indexed chunks.
```

---

# 18. Integrated the New Graph with ChatService

Updated `ChatService` to invoke the LangGraph workflow.

The chat flow is now:

```text
Frontend
 ↓
Chat API
 ↓
Authentication
 ↓
ChatService
 ↓
LangGraph
 ↓
Agent
 ↓
Tool Decision
 ↓
Tool Node (if required)
 ↓
Final Answer
 ↓
ChatService
 ↓
Save Assistant Message
 ↓
Frontend
```

The authenticated user's identity is passed into the graph so tools remain user-scoped.

---

# 19. Completed End-to-End Week 9 Testing

Finally, the complete Week 9 implementation was tested through the application flow.

Verified:

### No-tool requests

```text
Hello
2 + 2
```

Gemini answers directly without unnecessary tool execution.

### Document questions

```text
What did the mysterious device reveal?
```

The Agent selects:

```text
search_documents
```

and uses the existing RAG pipeline.

### Workspace questions

```text
How many documents do I have?
```

The Agent selects:

```text
get_workspace_stats
```

and converts the structured result into a natural-language answer.

### Web questions

The Agent can select:

```text
web_search
```

and use Tavily results before generating the final answer.

**Week 9 is therefore implemented and end-to-end tested successfully.**
