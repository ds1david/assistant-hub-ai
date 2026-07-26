# Plan: R4 Visual Context P0 (#68)

1. Schema `visual-frame-event.v1.schema.json`
2. session-core: `PiiMasker`, `OcrEngine` (Fake), `VisualFrameService`, REST POST/GET
3. Persist as HubEvent type `visual.frame.v1` via SessionRepository (Memory Hub reuse)
4. Shell panel + Tauri wrappers
5. Tests without GPU/display
