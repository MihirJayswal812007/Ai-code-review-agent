# Enhanced Documentation with Visual Examples

This document contains visual mockups and examples to be integrated into the README.

## 1. Example: AI Code Review Inline Comment

![AI Review Comment Example](example_review_comment.png)

**Mockup of AI Code Review Comment:**

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🟡 WARNING — Potential Null Pointer Risk                           │
│                                                                     │
│ Category: bug                                                       │
│                                                                     │
│ The variable `user_data` is accessed without checking if it's      │
│ None. This could lead to an AttributeError at runtime if the       │
│ database query returns no results.                                 │
│                                                                     │
│ Suggested fix:                                                      │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ # Add null check before accessing                           │   │
│ │ if user_data is None:                                       │   │
│ │     return {"error": "User not found"}                      │   │
│ │ return user_data.to_dict()                                  │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ 🤖 Posted by AI Code Review Agent                                  │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. Example: PR Summary Comment

```
┌────────────────────────────────────────────────────────────────────┐
│ 🤖 AI Code Review Summary                                          │
│                                                                    │
│ Quality Score: 7.5/10 🟢🟢🟢🟢🟢🟢🟢🟢⚫⚫                          │
│                                                                    │
│ ┌──────────────────────┬──────────┐                               │
│ │ Metric               │ Count    │                               │
│ ├──────────────────────┼──────────┤                               │
│ │ Total Issues         │ 5        │                               │
│ │ 🔴 Critical          │ 1        │                               │
│ │ 🟡 Warnings          │ 3        │                               │
│ │ Files Reviewed       │ 8        │                               │
│ └──────────────────────┴──────────┘                               │
│                                                                    │
│ Summary: Found 5 issue(s) across 8 file(s). Overall quality       │
│ score: 7.5/10.                                                     │
│                                                                    │
│ 📁 File Breakdown                                                  │
│                                                                    │
│ - `src/app.py` — ⚠️ 2 issue(s)                                    │
│ - `src/github_client.py` — ✅                                     │
│ - `src/llm_reviewer.py` — ⚠️ 1 issue(s)                           │
│ - `src/diff_parser.py` — ✅                                       │
│ - `src/models.py` — ⚠️ 2 issue(s)                                 │
│                                                                    │
│ ---                                                                │
│ Powered by AI Code Review Agent 🤖                                 │
└────────────────────────────────────────────────────────────────────┘
```

## 3. Detailed Workflow Sequence Diagram

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant GH as GitHub
    participant Webhook as AI Review Server
    participant Groq as Groq API<br/>(Llama 3.3)
    participant Bot as Review Bot

    Dev->>GH: Opens Pull Request
    Note over GH: Triggers webhook event
    GH->>Webhook: POST /webhook<br/>(PR payload)
    
    Webhook->>Webhook: Verify HMAC signature
    alt Invalid signature
        Webhook-->>GH: 401 Unauthorized
    end
    
    Webhook->>GH: GET /repos/{owner}/{repo}/pulls/{pr}/files
    GH-->>Webhook: Raw diff + file list
    
    Webhook->>Webhook: Parse diff into chunks
    Note over Webhook: Split by language,<br/>chunk by size
    
    loop For each code chunk
        Webhook->>Groq: Analyze chunk<br/>(system + user prompt)
        Groq-->>Webhook: Issues JSON:<br/>{severity, category,<br/>description, suggestion}
    end
    
    Webhook->>Webhook: Aggregate results<br/>Calculate quality score
    
    Webhook->>GH: POST Review<br/>(summary + inline comments)
    GH-->>Webhook: 201 Created
    
    GH->>Bot: Review posted
    Bot->>Dev: Notification:<br/>"Your PR has been reviewed"
    
    Dev->>GH: Views review comments
    Note over Dev,GH: Developer makes fixes<br/>based on feedback
```

## 4. Architecture Component Interaction

```mermaid
graph LR
    subgraph "External Services"
        A[GitHub API]
        B[Groq LLM API]
    end
    
    subgraph "AI Review Agent Core"
        C[FastAPI Server]
        D[GitHub Client]
        E[Diff Parser]
        F[LLM Reviewer]
        G[Comment Formatter]
    end
    
    subgraph "Data Models"
        H[Pydantic Models]
        I[Config/Settings]
    end
    
    A -->|Webhook Event| C
    C -->|Parse Payload| H
    C -->|Get Diff| D
    D <-->|REST API| A
    D -->|Raw Diff| E
    E -->|Chunks| F
    F <-->|Chat API| B
    F -->|Issues| G
    G -->|Formatted| D
    D -->|Post Review| A
    
    I -.->|Configure| C
    I -.->|Configure| D
    I -.->|Configure| F
    
    style C fill:#4CAF50,stroke:#2E7D32,color:#fff
    style F fill:#2196F3,stroke:#1565C0,color:#fff
    style B fill:#FF9800,stroke:#E65100,color:#fff
    style A fill:#9C27B0,stroke:#6A1B9A,color:#fff
```

## 5. Performance Metrics (Example)

```mermaid
pie title Review Response Time Distribution
    "< 5 seconds" : 45
    "5-10 seconds" : 35
    "10-20 seconds" : 15
    "> 20 seconds" : 5
```

## 6. Language Support

```mermaid
pie title Supported Languages
    "Python" : 40
    "JavaScript" : 25
    "TypeScript" : 20
    "Java" : 10
    "Others (extensible)" : 5
```

## 7. Usage Statistics Example

```
┌─────────────────────────────────────────────────────────┐
│ 📊 Project Statistics                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Total Reviews:           127                           │
│  Issues Found:            438                           │
│  Critical Issues:          45 (10%)                     │
│  Avg Quality Score:       8.2/10                        │
│  Avg Review Time:         7.3s                          │
│                                                         │
│  Top Issue Categories:                                  │
│    1. Best Practice    35%  ████████████████████        │
│    2. Code Style       30%  ████████████████            │
│    3. Bugs             20%  ███████████                 │
│    4. Security         10%  █████                       │
│    5. Performance       5%  ███                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```
