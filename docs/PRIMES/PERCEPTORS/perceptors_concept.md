Perceptors – Concept and Design
Overview
Perceptors are the sensory entry points of PABLO. They continuously sample the external world (and internal mind) to provide raw observations that feed into the cognitive pipeline. There are three primary perceptors, each corresponding to a modality:

READ – text/linguistic input (e.g., console, files, screen text)

SEE – visual input (e.g., simulated scenes, camera feeds, screen content)

HEAR – auditory input (e.g., simulated sounds, microphone)

Perceptors operate autonomously in the background, much like our own senses, and can also be consulted on‑demand for focused perception. They are the first step in transforming raw sensory data into prime‑grounded compounds.

Core Principles
1. Autonomy
Each perceptor operates continuously and independently, sampling its environment without external coordination. This mirrors the always‑on nature of biological perception.

2. Decentralization
Perceptors are independent; they do not depend on each other or on higher‑level cognition to function. They simply emit observations that are then processed by downstream components.

3. Perceptor Exemption Rule
In autonomous mode (background sampling), perceptors emit raw observations—they are exempt from the compound‑only rule that applies elsewhere. This allows raw data to flow freely into the system. In consultation mode (when invoked directly by another prime), they return proper compounds.

4. Flood Protection
Perceptors avoid overwhelming the system with redundant observations. They track recently emitted events and suppress duplicates that occur within a short time window. This ensures that only meaningful, non‑repetitive inputs enter the pipeline.

5. Change‑Driven Ingestion
Perceptors are designed to detect meaningful change rather than ingest raw data continuously. They maintain internal state about what they are sensing and emit an observation only when a significant change occurs—such as the appearance, disappearance, or state transition of an object in view, new text appearing on screen, or a new sound event. This principle drastically reduces noise and focuses the system on semantically relevant events.

6. Extensibility
Perceptors are structured to accommodate new input sources and modalities without altering their core logic. Change‑detection strategies can be adapted per modality.

High‑Level Interaction
Perceptors emit raw observations into a shared communication channel (e.g., a queue). Downstream, the DATA prime consumes these observations, structures them, and passes them to KNOW for storage and further processing. This separation keeps perceptors simple and focused solely on sensing.

In consultation mode, a perceptor is called directly (e.g., by THINK) and returns a compound representing the requested perception immediately.

Change Detection by Modality (Conceptual)
SEE (video): The perceptor maintains a lightweight model of the visual scene. It tracks objects and their states, and emits an observation only when an object appears, disappears, or changes its semantic state (e.g., stationary → moving, rolling → in‑air). A static scene generates no new observations.

READ (text): For streaming text (e.g., console input), each new line is a change. For static screen text, the perceptor monitors the text region and emits an observation only when the content changes (e.g., new text appears, text is cleared).

HEAR (audio): The perceptor listens for sound events—a dog bark, a door slam, a voice onset—and emits an observation when such an event occurs, rather than streaming continuous audio.

Design Decisions Summary
Decision	Rationale
Perceptors operate continuously and independently	Enables always‑on sensing without blocking other processes
Autonomous output is raw observations (not compounds)	Allows raw data to flow freely; maintains simplicity
Flood protection prevents duplicate observations	Reduces downstream noise and unnecessary processing
Change‑driven ingestion focuses on semantic events	Avoids ingesting static data; highlights meaningful transitions
Consultation mode returns compounds	Aligns with prime‑based communication when focused perception is needed
Shared downstream processing (DATA/KNOW)	Decouples sensing from structuring and storage
Extensible to new sources	Future‑proofs the design
Example Scenarios
Video Scene with a Ball
The ball appears → observation emitted.

The ball rolls across the scene → observation emitted when rolling starts.

The ball stops → observation emitted when it becomes stationary.

The scene is otherwise static → no further observations until another change occurs.

Screen Text
A terminal window displays “Hello”. No observation (assuming it was already present).

The user types “ world” → the text changes; a new observation (“ world”) is emitted.

The screen clears → an observation (“screen cleared”) is emitted.

Consultation Mode
THINK needs the current screen content and calls READ directly. READ returns a compound containing the full text, bypassing change detection.

Future Extensions (Conceptual)
Attention‑guided sensing: WANT could influence which changes are considered meaningful (e.g., focus on objects relevant to current goals).

Multi‑modality fusion: Later, perceptors might share information to detect cross‑modal events (e.g., a visible object and a related sound).

Learning trackers: For video, lightweight learned models could improve object tracking and state classification.

Relationship to Other Primes
DATA consumes raw observations, now a sparse stream of meaningful events.

KNOW stores the resulting compounds, building a timeline of semantic changes.

THINK can invoke perceptors on‑demand and also benefits from the concise event stream for reasoning.

WANT may provide top‑down attention to bias change detection.

Perceptors are the gateway through which the world enters PABLO. By sensing intelligently—detecting change, avoiding redundancy—they lay the foundation for efficient, focused cognition.