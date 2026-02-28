PABLO GUI – Visual Design


This document defines the visual design and UX flow of the PABLO interface. Implementation details (panel interface, queue contracts, threading) live in GUI_ARCHITECTURE.md.


Screen Flow
PABLO has two screens. The user moves through them in one direction at boot; they can return to the boot screen on shutdown.

  ┌─────────────────┐       boot button        ┌─────────────────┐
  │   Boot Screen   │  ──── all primes ready ──▶│   Main Screen   │
  │  (splash/logo)  │                           │  (workspace)    │
  └─────────────────┘  ◀── shutdown ────────────└─────────────────┘


1. Boot Screen
The first thing the user sees. Black background. Centre of the screen.

Logo
An animated 3D blob — an organic, softly morphing shape rendered in dark blues, teals, and subtle reds. It floats and slowly reshapes, like a living thing at rest. Implemented as a Three.js canvas embedded in NiceGUI via `ui.html` — a self-contained script tag so there is no build step.

The blob uses:
- A sphere geometry with Perlin-noise vertex displacement animated over time
- Point cloud rendering (not solid mesh) — individual dots of light, not a filled surface
- Additive blending so overlapping points glow brighter at dense areas
- A slow rotation on the Y axis
- Colour shifts between deep teal (#00c8c8), electric blue (#0044ff), and dim red (#440011) as the shape evolves

The blob is not a loader — it is PABLO's visual identity. It is present on the boot screen whether PABLO has started or not.

Status text
Below the blob, a small line of muted text. States:

  "PABLO"                        ← default, before boot
  "Initialising..."              ← boot button pressed, primes starting
  "READ online."                 ← each prime reports in, replacing the previous line
  "SYMBOL online."
  "DATA online."
  "KNOW online."
  "THINK online."
  "Ready."                       ← all primes running; screen transitions after 1.2 s

Font: monospace, small, low-contrast (e.g. #888888 on black). No animation — just text replacement.

Boot button
A single button centred below the status text. Minimal — outlined, not filled. Text: "Initialise".

On click:
1. Button disappears.
2. Status text begins cycling through prime startup messages.
3. The blob animation speeds up slightly during initialisation.
4. On "Ready." the blob pulses once (brief brightness spike), then the screen cross-fades to the Main Screen.

The boot button is only shown when PABLO is not yet initialised. It does not reappear unless PABLO is shut down.

Boot screen layout (centred column):

  ┌─────────────────────────────────────────────────────┐
  │                                                     │
  │                                                     │
  │                    [ blob ]                         │
  │                                                     │
  │               "PABLO"  (status text)                │
  │                                                     │
  │                  [ Initialise ]                     │
  │                                                     │
  └─────────────────────────────────────────────────────┘


2. Main Screen
After initialisation. The blob persists — it moves to the top-left corner, small, as a persistent identity mark. It continues its idle animation at low speed.

The main screen is a tabbed workspace. Each tab is a section of PABLO's interface.

Tab bar (top, full width):
  [ Talk ]  [ Inspect ]  [ Statistics ]  [ Settings ]

Phase 1: only Talk is implemented. The other tabs are visible but show a "Not yet implemented" placeholder when selected — they are not hidden, so the user can see what is coming.


2a. Talk Tab (Phase 1 — active)
The primary interface. Occupies the full main area below the tab bar.

Layout:

  ┌─────────────────────────────────────────────────────┐
  │ [●] PABLO                           [blob, small]   │
  ├─────────────────────────────────────────────────────┤
  │ [ Talk ]  [ Inspect ]  [ Statistics ]  [ Settings ] │
  ├─────────────────────────────────────────────────────┤
  │                                                     │
  │  YOU      12:04:01                                  │
  │  the cat moved left                                 │
  │                                                     │
  │  PABLO    12:04:02                                  │
  │  [response text]                                    │
  │                                                     │
  │  ...                                                │
  │                                                     │
  │                                           ▼ scroll  │
  ├─────────────────────────────────────────────────────┤
  │  [  type something...                 ]  [ Send  ]  │
  └─────────────────────────────────────────────────────┘

Conversation area:
- Dark background, full height between tab bar and input bar.
- Messages are left-aligned, not chat-bubble style. Clean, text-first.
- YOU messages: muted label, slightly dimmer text colour.
- PABLO messages: muted label, bright white text.
- Each message block: speaker label on one line, text below it, small timestamp to the right of the label.
- Thinking indicator: when PABLO has received input but not yet responded, a subtle animated ellipsis appears as a PABLO entry ("..."). Replaced by the actual response when it arrives.
- Auto-scrolls to bottom on new content. User can scroll up freely; auto-scroll resumes on new content only if already at the bottom.

Input bar:
- Full width. Rounded input field, placeholder text "type something...".
- Send button on the right. Keyboard shortcut: Enter.
- On send: text is cleared, message appears immediately in the conversation as a YOU entry, thinking indicator appears.
- Input bar is always enabled once on the Talk tab (primes are running by this point).


2b. Inspect Tab (future)
Browse PABLO's internal compound storage. Search by prime mask, text, or time range. View a compound's full prime breakdown. Not implemented in Phase 1 — shows placeholder.


2c. Statistics Tab (future)
Live charts: queue depths over time, observations per minute, compound creation rate, prime activity. Not implemented in Phase 1 — shows placeholder.


2d. Settings Tab (future)
Configure prime parameters, queue sizes, UI preferences (theme, font size, blob animation speed). Not implemented in Phase 1 — shows placeholder.


Visual Language
Colour palette:
  Background      #0a0a0a    near-black
  Surface         #111111    card/panel backgrounds
  Border          #1e1e1e    subtle separators
  Text primary    #f0f0f0    main readable text
  Text muted      #555555    labels, timestamps, placeholders
  Accent teal     #00c8c8    active tab indicator, blob primary colour, button border
  Accent blue     #0044ff    blob secondary colour, links
  Error           #ff4444    error states

Typography:
  UI labels, tabs:  Inter or system-ui, 13px, regular
  Conversation:     Inter or system-ui, 15px, regular
  Timestamps:       monospace, 11px, muted
  Status text (boot screen): monospace, 13px, muted

Motion:
  Screen transitions: cross-fade, 400ms ease
  Boot status text: instant replacement (no fade — feels like a terminal)
  Blob idle: slow, ~8s cycle
  Blob during init: faster, ~3s cycle
  Blob pulse on ready: single brightness spike, 300ms
  Thinking ellipsis: simple 3-dot fade cycle, 1s

All motion is subtle. This is a tool for sustained use — nothing flashes, bounces, or demands attention.


Blob Implementation Note
The blob is a Three.js scene embedded via `ui.html`. It is entirely self-contained — no external CDN call at runtime is required if Three.js is bundled locally. The script receives control signals (speed, pulse) from the Python side via NiceGUI's `ui.run_javascript()` calls triggered by the startup sequence.

Control signals:
  pablo.blob.setSpeed(1.0)     ← idle
  pablo.blob.setSpeed(3.0)     ← initialising
  pablo.blob.pulse()           ← ready flash
  pablo.blob.shrink()          ← transition to main screen (shrinks to corner)


See GUI_ARCHITECTURE.md for panel interface, queue contracts, and threading rules.
See CONCEPT.md for what each panel's data comes from.
