# Progress Log

## Working Style
- Follow the spec order strictly: data model, core bit manipulation, storage, then CLI.
- Keep this document updated with completed phases and blockers.
- Prefer simple, testable functions over premature optimization.

## Phase Plan
1. Core data conversion and bit manipulation
2. Round-trip encode/decode on a generated test image
3. Stop marker support for variable-length messages
4. CLI wrapper and basic validation
5. Optional password-based encryption

## Current Status
- [x] Project specification reviewed
- [x] Core binary conversion functions implemented
- [x] Encode/decode round-trip verified
- [ ] CLI workflow wired up
- [ ] Optional encryption layer added
