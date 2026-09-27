# Multi Agent Complaint Resolution
### AI for Fintech | [A2A-001]

A template architecture for agents that delegate to other agents. One orchestrator receives a customer complaint, delegates to two specialist agents that each own a domain, and consolidates their answers into a single response.

The orchestrator has no database access and no domain knowledge. It discovers what each agent can do by reading their agent cards, and delegates in plain language. Adding a third domain means starting a new server and adding one line to the registry.

---

## Architecture

![Architecture Multi Agent Complaint Resolution](Architecture%20Multi%20Agent%20Complaint%20Resolution.png)

Three layers, each one replaceable without touching the others:

```
ORCHESTRATOR    delegates and consolidates, knows no domain
A2A             discovery through agent cards, tasks over JSON-RPC
DOMAIN AGENTS   own their data, their tools and their prompt
```

---

## What This Solves

A customer complains about a charge they do not recognize. Answering that well needs two different things: what actually happened on that specific account, and whether the bank has seen this complaint before.

Those two things live in different systems, owned by different teams. The transactions team knows the individual case but not the pattern. The complaints team knows the pattern but cannot see the account.

The usual approach is to build an integration between them, then another integration when a third system joins, and so on. A2A replaces that with a protocol: each team publishes an agent, and the orchestrator discovers what it can do without any custom integration code.

---

## A2A and MCP

The two protocols solve different problems and are often used together.

MCP is vertical: it connects one agent to its tools. That is what the [MCP-001](https://github.com/junidepieri-design/mcp-001-fintech-data-server) project in this hub does.

A2A is horizontal: it connects agents to each other. The caller sends a task and receives an answer, without knowing which tools ran behind it. That opacity is the point: the transactions team can change their entire tooling and the orchestrator never notices.

In this project both appear. The orchestrator talks to the domain agents over A2A. Each domain agent uses its own tools internally.

---

## How It Works

A customer writes:

```
Customer 1042 says their statement has a charge of 49.90 they do not recognize.
```

The orchestrator reads both agent cards, decides it needs both domains, and delegates:

```
to transactions   Customer 1042 has a charge of 49.90 they do not recognize.
                  Can you find this charge and provide details?

to complaints     A customer does not recognize a charge of 49.90. Does this
                  match a known complaint pattern?
```

Notice the second question does not mention the merchant. At that point the orchestrator does not know it yet. The complaints agent identifies the pattern on its own.

The answers come back:

```
transactions      Recurring charge of 49.90 from StreamFlix, third occurrence,
                  billed August 12 and September 12, no refund issued.

complaints        Known pattern PAT-201. Free trial converted into a paid
                  subscription. Standard resolution is cancel and refund the
                  last two occurrences, 94% success rate, 340 cases in 30 days.
```

Neither agent had the complete answer. The orchestrator consolidates them, explains the likely cause and proposes the resolution.

---

## Project Structure

```
a2a-001-multi-agent-complaint-resolution/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── demo.py
├── config/
│   ├── __init__.py
│   └── a2a_config.py
├── orchestrator/
│   ├── __init__.py
│   ├── agent.py              delegation loop
│   ├── a2a_client.py         discovery and task sending
│   └── prompts/
│       └── system.md
├── agents/
│   ├── __init__.py
│   ├── transactions/
│   │   ├── __init__.py
│   │   ├── server.py         A2A server
│   │   ├── agent_card.json   what this agent can do
│   │   ├── agent.py          tool calling loop
│   │   ├── tools.py
│   │   └── prompts/
│   │       └── system.md
│   └── complaints/
│       └── (same structure)
└── data/
    ├── __init__.py
    └── generate.py
```

Each agent is a self contained folder. Adding a domain means copying one and registering its URL.

---

## Quickstart

### 1. Install

```bash
git clone https://github.com/junidepieri-design/a2a-001-multi-agent-complaint-resolution.git
cd a2a-001-multi-agent-complaint-resolution

py -3.13 -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Set your API key

Copy `.env.example` to `.env` and fill it in.

```
ANTHROPIC_API_KEY=your_key_here
```

Every agent in this project calls an LLM, which is what makes them agents rather than tools. The orchestrator uses a stronger model because it decides and consolidates. The domain agents use a smaller one because they only pick a tool and format the result.

### 3. Generate the demo data

```bash
python -m data.generate
```

Five records per domain, written to a local SQLite database. The data is intentionally small: what matters here is the architecture, not the volume. The records are built to support the demo case end to end, so the two domains reference the same charge.

### 4. Start both agents

Each agent is an independent HTTP server. Open one terminal for each.

```bash
uvicorn agents.transactions.server:app --port 8001
```

```bash
uvicorn agents.complaints.server:app --port 8002
```

You can confirm an agent is up by opening its card in a browser:

```
http://localhost:8001/.well-known/agent.json
```

### 5. Run the demo

```bash
python demo.py
```

Or with your own case:

```bash
python demo.py "customer 1087 says a refund was approved but never credited"
```

The output shows the discovery, every delegation with the question and the answer, and the consolidated response.

---

## Adding a Domain Agent

Three steps, none of them in the orchestrator.

Copy one of the agent folders and rename it. Rewrite its `tools.py` against your data, its `agent_card.json` describing what it can do, and its `prompts/system.md` telling it what it knows and what it does not.

Register the URL in `config/a2a_config.py`:

```python
AGENT_REGISTRY = {
    'transactions': 'http://localhost:8001',
    'complaints': 'http://localhost:8002',
    'your_domain': 'http://localhost:8003'
}
```

Start the server. The orchestrator builds its delegation tools from the cards at runtime, so it starts using the new agent without any code change.

---

## Key Design Decisions

**The orchestrator owns no data.** It has no database connection and no domain tools. Every tool it has is a delegation. This is what lets each team keep their data, their logic and their model choice without negotiating with whoever maintains the orchestrator.

**Delegation tools are built from agent cards at runtime.** The orchestrator reads the cards on every run and generates one tool per agent from the description and skills. Nothing about the domains is hardcoded.

**Each agent prompt says what it does not know.** The transactions agent is told it knows nothing about complaint patterns. The complaints agent is told it cannot see accounts. Without that, an agent tries to answer outside its domain and delegation stops happening.

**Questions travel in plain language.** The orchestrator asks the way it would ask a colleague from another team. It never asks which tools an agent has or how it stores data, because that is exactly what A2A is meant to hide.

**Opaque execution is enforced by the protocol, not by convention.** The A2A response carries only the answer. Tool names and query results never cross the boundary, so a domain team can rewrite their internals without breaking anyone.

**Delegation rounds are capped.** Without a limit, agents calling agents can loop. The cap lives in the config.

**One file knows the wire format.** All the A2A protocol details live in `a2a_client.py`. Replacing A2A with something else means rewriting that file and nothing more.

---

## Terms Explained

| Term | What It Means |
|---|---|
| A2A | Agent2Agent, an open protocol for agents to discover and delegate to each other. Released by Google in April 2025, now under the Linux Foundation. |
| Agent Card | A JSON document at `/.well-known/agent.json` describing what an agent can do. How discovery works. |
| Opaque execution | Agents interact without sharing internal logic or tools. The caller sees the answer, never the path to it. |
| Orchestrator | The agent that receives the request, delegates to others and consolidates. Also called the client agent. |
| Domain agent | An agent that owns a subject and answers questions about it. Also called a remote agent. |

---

## What v2 Would Look Like

Running this beyond a demo means adding what any network service needs. A2A supports authentication between agents, which matters once they run on different hosts. Long running tasks need the streaming and push notification capabilities the protocol defines, both declared as false in the cards here. And in a regulated environment every delegation needs to be logged, because the audit question is not only what the customer was told but which systems were consulted to tell them.

---

## Author

Built by [Odemir Depieri Jr](https://www.linkedin.com/in/odemir-depieri-jr/), Data and AI specialist with 14 years of experience in data and AI within banks and financial institutions.

Part of the AI for Fintech applied research hub.