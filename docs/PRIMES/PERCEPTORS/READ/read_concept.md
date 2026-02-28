READ – Concept and Design


Overview
READ is PABLO's linguistic perceptor. It is the system's ability to encounter written language in the world — text the user types, text visible on screen, and text stored in files. READ does not interpret what language means; it detects that language has appeared or changed and delivers that raw event downstream for SYMBOL to interpret.

READ is the first and currently only active perceptor. Everything that enters PABLO's cognitive pipeline as text arrives through READ.


What READ Senses
READ monitors a set of text sources. Each source corresponds to a different way text exists in the world:

KEYBOARD — text typed by the user in real time (NiceGUI input bar).
The user types a line and presses Send (or Enter) in the GUI. The NiceGUI Send callback calls GUIInputSource.inject(text), which queues the text for READ's autonomous loop to pick up via acquire(). This is the only active source in Phase 1.

The concrete implementation is GUIInputSource (gui/input_source.py). It replaces stdin entirely. For headless or test runs, a StdinSource can be substituted — the loop is unchanged.

SCREEN — text visible on the screen (screen reader / OCR region).
READ monitors one or more screen regions for text content. When the content changes — new text appears, existing text changes, or text is cleared — READ emits an observation. Dormant until implemented.

FILE — text inside a watched file or set of files.
READ monitors file contents for appended or modified text, similar to tail -f. Useful for log files, shared memory files, or any text file written to by external processes. Dormant until implemented.

All three sources share the same output contract: a raw observation dict pushed to observation_queue. Sources that are not yet implemented are registered as dormant placeholders so they can be activated without changing any downstream code.


Change Detection
READ is not a line-by-line reader — it is a change detector. For each source, "sensing" means detecting a meaningful transition in text state:

KEYBOARD: a new non-empty line is a change. An empty Enter press is not. Repeated identical lines within the cooldown window are suppressed.

SCREEN: a change in the text content of a monitored region is a change. A static screen generates no observations. The comparison is text-level (hash of the visible text), not pixel-level.

FILE: new bytes appended beyond the last-known file position is a change. Each new logical line (or configurable chunk) produces one observation.

Nothing reaches the queue unless a change has occurred. A perceptor observing a static world produces zero output.


Relationship to SYMBOL
READ's output is the primary input to SYMBOL's autonomous thread. SYMBOL pulls from observation_queue and interprets READ observations first because text is PABLO's primary modality in Phase 1.

What SYMBOL needs from READ:
- event_type — so the right specialist is invoked (keyboard input needs different handling than file content).
- data.text — the raw string to interpret.
- metadata.source — for provenance tracking in the resulting compound.

READ does not care what SYMBOL does with its output. The observation dict is READ's complete contract. Any change to that contract requires updating both READ and SYMBOL together.


Consultation Mode
READ can be called on-demand by THINK (or any other prime) to fetch current text synchronously. In consultation mode:
- Change detection is bypassed — READ returns whatever is currently available.
- The queue is not used — the result is returned directly to the caller as a Compound.
- This lets THINK ask "what is being typed right now?" without waiting for the autonomous loop.


Source Taxonomy Summary
Source        Status    Phase 1    Concrete class          What triggers an observation
KEYBOARD      active    yes        GUIInputSource          New non-empty line submitted via the GUI input bar
SCREEN        dormant   no         ScreenSource (stub)     Text region content changes
FILE          dormant   no         FileSource (stub)       New content appended to a watched file


Simulation
READ includes a simulation facility for testing. It feeds pre-defined strings into the pipeline as if they had arrived from the KEYBOARD source. This is strictly a test tool — it is gated behind an explicit flag and removed before production use. It has no effect on the production loop.


See READ_ARCHITECTURE.md for implementation details.
See PERCEPTORS/CONCEPT.md for the general perceptor contract.
See PRIMES/SYMBOL/CONCEPT.md for how SYMBOL consumes READ's output.
