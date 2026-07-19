# Browser QA and release evidence

Tested on 2026-07-19 with Chrome 150.0.7871.125 on Windows. The hosted build was produced with `STATIC_EXPORT=true`, `BASE_PATH=/causalpilot`, and `NEXT_PUBLIC_API_BASE_URL=offline`; the live journey used the local Next.js client against the FastAPI service on port 8000.

## Outcome

- Desktop 1440×900, tablet 768×1024, and mobile 375×812 all rendered the WebGL topology with no document-level horizontal overflow.
- All four mobile mission controls remained fully inside the 375 px viewport and met the 44 px touch-target height.
- Chrome console errors, page errors, and failed requests: **0** in the final static run.
- axe-core violations: **0** on desktop and mobile. Gradient-backed text remains an automated `color-contrast` incomplete/manual-review item; the one determinable 3.19:1 violation found earlier was fixed and the final scan reports no violation.
- Keyboard focus uses a visible 2 px cyan outline. The displayed `R` shortcut starts the mission. Timeline review is read-only and does not mutate the API state.
- With `prefers-reduced-motion: reduce`, automatic playback stays off and CSS transitions collapse to 0.001 ms; an explicit `R` action still starts playback.

## Critical journeys

### Static hosted replay

The production export loaded with the permanent `STATIC REPLAY · SIMULATED SCM` badge. Reset, keyboard start, timeline review, all six narrative stages, and the final dynamically computed `SAFE SCOPE / WITHHOLD` readout worked without network fallbacks.

### Live API authorization path

The browser exercised the real state machine in this order:

```text
start → diagnose → experiment → drift(new_arrivals)
      → ask_human → answer(margin_floor=0.15, subsidy_cap=8)
      → segment_deploy
```

Every request returned HTTP 200 and the final backend state was `deployed`. Invalid early drift/human controls are disabled, manual jumps no longer double-POST, and non-2xx responses are not counted as successful live evidence.

## Performance snapshot

These are local headless measurements, not field Core Web Vitals:

| Run | DCL | Load | FCP / LCP | CLS | Interaction proxy |
| --- | ---: | ---: | ---: | ---: | ---: |
| Cold production load | 0.618 s | 1.725 s | 2.108 s | 0.000053 | — |
| Warm production load | 1.241 s | 1.696 s | 1.284 s | 0.000011 | 80 ms max Event Timing |

The Three.js scene is an asynchronous chunk: the semantic control room paints first, a fixed-size topology placeholder prevents layout shift, and the interactive canvas mounts afterward.

## Visual and video artifacts

- Hero screenshot: `docs/assets/control-room-final.png` — SHA-256 `a5cff733673b70c585d8d19dde32557a4af8cf753ac551140ae3d87b02527160`.
- Responsive captures: `docs/assets/control-room-tablet.png` and `docs/assets/control-room-mobile.png`.
- Demo video: `docs/assets/causalpilot-demo.mp4` — exactly 90.00 s (2,250 frames), H.264 High/yuv420p, 1280×720, 25 fps, SHA-256 `777dfd7f815fea4c5b937a55f887a5c14148193644020aa87397f75181d92b8c`.

## Known boundaries

- The public page is a deterministic simulated replay; only the local setup connects to the mutable FastAPI engine.
- The 3D canvas receives a descriptive accessible name, but its spatial relations remain visual; the same segment status and metrics are repeated as DOM text.
- Performance varies with GPU/WebGL implementation. The numbers above are a release smoke test, not real-user monitoring.
