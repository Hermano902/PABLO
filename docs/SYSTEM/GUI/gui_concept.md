PABLO GUI – Concept


What the GUI Is
The GUI is PABLO's interface to the outside world — the surface through which a human communicates with the system and observes what it is doing. It is not part of the cognitive pipeline. It does not reason, store, or interpret. It does two things: deliver text from the user into the pipeline via READ, and surface the system's internal state and outputs back to the user.

The GUI is a window into a running mind, not the mind itself. Every prime, queue, and compound operates identically whether the GUI is present or not. The GUI is replaceable without touching a single line of cognitive code.


Technology: NiceGUI
The GUI is implemented with NiceGUI.

- Runs locally and remotely without code changes — same codebase on a laptop or a cloud server.
- Accessible from any browser including mobile. Nothing to install on the client.
- Full CSS/Tailwind customisation when needed.
- Real-time bidirectional updates via WebSockets — output appears live as PABLO produces it.
- Pure Python. No JavaScript required to build or customise.
- NiceGUI uses FastAPI internally. If a separate frontend (React, mobile app) is needed later, the FastAPI backend is already there and the cognitive core is untouched.


Role in the Pipeline
The GUI touches the pipeline at exactly two points:

  User types text
      ↓
  GUIInputSource (inside READ)  ← the only path user input takes into the system
      ↓ observation_queue
  SYMBOL → DATA → KNOW → THINK  (unaffected — no GUI knowledge)
      ↓ response_queue
  GUI output panel
      ↓
  User sees response

GUIInputSource is registered as READ's active keyboard source. It pushes the same canonical observation dict that any source would. Nothing downstream knows or cares that the text came from a browser form rather than a terminal.

THINK pushes responses to response_queue. The GUI polls that queue and displays results. Background prime threads never call any GUI function directly — the queue is the only coupling.


Layout – Phase 1
Three panels in a fixed layout:

┌─────────────────────────────────────────────────────────┐
│  PABLO                                          [status] │
├───────────────────────────────┬─────────────────────────┤
│                               │                         │
│   Conversation                │   System                │
│                               │                         │
│   [output log]                │   Primes:  READ ● ...   │
│                               │   Queues:  obs  42/10k  │
│                               │            cand  0/10k  │
│                               │            resp  0/10k  │
│                               │                         │
│                               │   [event log]           │
│                               │                         │
├───────────────────────────────┴─────────────────────────┤
│  [input box]                              [Send]         │
└─────────────────────────────────────────────────────────┘

Conversation panel (left, main)
The running exchange between the user and PABLO. Each entry has a timestamp, a speaker tag (YOU / PABLO), and the text. Responses appear incrementally — no waiting for a complete answer. Read-only.

System panel (right, sidebar)
Live visibility into what the pipeline is doing. Shows prime status (running / idle / error), queue depths (observation, candidate, response), and a rolling event log of internal system events. Essential during development; stays useful in production for monitoring.

Input bar (bottom, full width)
Single-line text input and a Send button. Enter key submits. Cleared on submit. Disabled while PABLO is initialising.


Modularity
The GUI is panel-based. Each panel is independent — it owns its NiceGUI elements, receives a system state snapshot on each timer tick, and can be toggled off. Adding a new panel never touches existing panels.

Phase 1 panels: Conversation, System.

Future panels (examples):
- Compound Inspector — browse KNOW's compound storage, search by prime mask
- Pipeline Graph — live queue depth and throughput chart
- Memory Timeline — compounds on a time axis, filterable by modality or prime
- SELF Observer — meta-cognitive state, attention and goal biases
- Settings — configure prime parameters, queue sizes, UI preferences


Deployment Targets
Local: run on any machine, open in any browser.
Remote: deploy to any cloud server, access from anywhere including a phone.
No code changes between local and remote. The layout is responsive — the sidebar collapses on narrow screens.


What the GUI Is Not
- Not a prime. It has no role in reasoning, storage, or interpretation.
- Not a debugger. The System panel gives observability but the canonical debugging interface is tests and structured logging.
- Not stateful. The Conversation panel does not persist across page refreshes. Conversation history lives in KNOW and is queryable from there.


See GUI_ARCHITECTURE.md for panel interface, state bridge contracts, startup sequence, and deployment details.
See docs/PRIMES/PERCEPTORS/READ/READ_ARCHITECTURE.md for GUIInputSource.
See docs/SYSTEM/CONCEPT.md for the cognitive pipeline this GUI surfaces.
