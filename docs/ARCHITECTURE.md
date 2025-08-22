# Architecture (High-Level)

- **brain/**: kernel, event bus, scheduler, registry, global types.
- **io/**: senses (eyes/ears/system) and actuators (ui/filesystem/network/speech), each with local pipelines (sensors→decoders→recognizers→normalizers).
- **cognition/**: attention, context, working memory, general reasoning, planner, and pluggable skills (language, search, vision, math, automation).
- **memory/**: domain memories with two layers (L0 reference, L1 experience), plus semantic/episodic/vector stores and adapters.
- **daemons/**: default-mode network (idle idea surfacing), health checks.

> Update your `structure.json` and `pablopath.py` to include these new roots for clean imports.
