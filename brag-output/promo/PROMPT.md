# Ledger Lens: 18-second product promo, production prompt

This replaces the earlier template. It was rebuilt from a frame-by-frame study of the reference reel (Instagram `reels/Dd7ZNPGxiMw`, product segment 6.3s–23.2s): 69 frames at 0.25s steps, 12 full-resolution stills, pixel-sampled colours, and an analysis of the audio track (loudness, brightness, beat onsets). Part A records what the reference does. Part B is the prompt for Ledger Lens.

---

## Part A: What the reference actually does

### A1. Shot timing (reference seconds, from frame stepping)

| t (s) | Shot | Motion |
|---|---|---|
| 6.20 → 6.45 | Hard cut from the talking head | No transition. Instant cut to near-black |
| 6.45 → 7.20 | **Logo sting** | App icon (white rounded square, brand glyph) centred at ~20% frame width on near-black navy. Fades and scales up slightly (≈0.9→1.0) over ~0.25s with a soft white-blue bloom. Holds ~0.5s |
| 7.20 | Hard cut to the blue stage | A black-screened phone enters from below |
| 7.20 → 7.95 | **Phone rise** | Black phone (screen off) rises from below frame to slightly right of centre, tilted ~4° clockwise with a slight Y-axis turn (left edge nearer). Decelerating ease-out |
| 7.95 | **Screen wakes** | The app UI appears on the screen in one or two frames. The phone is now smaller (≈62% frame width), still tilted ~4° |
| 7.95 → 9.20 | Settle | The phone straightens to 0° and centres while scaling up slowly |
| 9.20 → 9.70 | **Push-in (on the beat drop)** | Fast camera push (≈0.4s, strong ease-out) until the phone's top half fills the frame |
| 9.70 → 12.70 | **Hero-card pop-out** | The navy revenue card lifts out of the screen: scale ≈1.2, counter-rotated ≈−3°, deep soft shadow. The rest of the screen is gaussian-blurred (~8–10px) and dimmed to a flat grey (≈#929092). The card's value ticks up as notifications arrive ($22.7K → $23.0K → $24.0K) |
| 10.45 / 11.20 / 11.70 | **Notifications** | iOS-style banners drop in from above the phone (white #fcfafc, 18px radius, blue app icon, small-caps app name, bold title, sub-line, "now" right-aligned). New banners stack on top and older ones peek behind, smaller and lower. One every ~0.5–0.75s |
| 10.45 → 12.45 | Caption 1 | **"EVERY SALE. LIVE."** in two lines, **lower-left**, over the blurred screen |
| 12.45 → 13.45 | **Pull-back** | The card sinks back in, the blur lifts, and the camera pulls back to the full phone (~1s) |
| 13.70 → 15.45 | Hold: dashboard | Phone square-on, centred, top at ~19% and bottom at ~96% of the frame height. Caption 2 **"YOUR WHOLE BUSINESS, AT A GLANCE."** top-left, words rising in one by one. Barely perceptible slow zoom |
| 15.45 → 15.95 | Transition to products | In-app tab change (the screen content changes) while the phone **tilts into 3D**: rotateY ≈ −12° (right side recedes), rotateZ ≈ −3° |
| 16.20 → 18.20 | Products | Caption 3 **"EVERYTHING YOU SELL."** top-left. The product grid scrolls up slowly inside the screen. The phone sways very slightly |
| 18.45 → 19.20 | Transition to orders | The tilt flips to the opposite side (top edge rising to the right). Caption 4 **"EVERY ORDER, TRACKED."** |
| 19.95 → 21.45 | **Order-card pop-outs** | Three order rows extrude out of the list, staggered ~0.25s apart. Each scales ≈1.15 and slides sideways past the phone edge, alternating left, right, left by ≈40–70px, with drop shadows. They hold ~1s, then slide back in ~0.3s |
| 22.20 → 22.70 | Bottom sheet | An order-detail **bottom sheet** slides up over the list (rounded top, grab handle, primary button at the bottom) |
| 22.95 | Caption 5 | **"ORDERS FROM ANYWHERE."** |
| 23.20 | Hard cut | Back to the talking head |

Throughout, a small persistent pill at bottom centre (≈97% height) reads **"Sample store: Maison Kano"** in white text on translucent grey (≈#858c9c).

### A2. Colour grade (pixel-sampled)

- **Logo sting background:** `#010111` (near-black navy), glow around the icon `#051328`, icon `#f7f6fc`.
- **Stage:** a cinematic blue vignette. A pool of light at top centre (`#095ec8` at 12% height, `#074aaa` at the top edge) falls off to deep navy at the sides (`#01225b` mid-height) and to near-black navy at the corners and bottom (`#001232`, `#02143a`). No hue shift and no gradient banding, just a smooth radial falloff. It reads as a spotlight from above.
- **Captions:** cool white, `#edf3fd`.
- **Blur dim:** the screen behind a popped card goes to flat neutral grey (`#8a8f92` to `#929092`), meaning blur plus about a 40–45% grey wash.
- **UI:** white and cool-grey surfaces, a deep royal-navy hero card, small green, purple and orange accents.

### A3. Typography

- **Captions:** a geometric grotesk at its heaviest weight (ExtraBold/Black), ALL CAPS, tight leading (~0.95), normal to slightly tight tracking, always two lines, left-aligned. Cap height is ≈4.5% of frame height. Top-left captions sit at ≈7% from the left and ≈6% from the top. Words enter one at a time: fade plus rise of ~0.02 frame-height, ~60–80ms apart.
- **UI:** a rounded geometric sans (Poppins-like), true-to-device sizes.

### A4. Phone and depth

- Thin graphite bezel with a faint light rim, dynamic island, side buttons, and a big, soft, dark-navy shadow under the phone.
- 3D: perspective tilt (rotateY ±12°) plus a small rotateZ (±3–4°). Never more than that. Motion is always eased, never linear.
- Pop-outs extend **past the phone edges**, which sells the depth.

### A5. Sound (measured)

- **The voice ends** at the cut into the sting.
- **Near silence** (−27 dB to −51 dB) covers the sting and the phone rise (≈7.2–9.0s), which builds tension.
- **The beat drops at 9.04s, exactly on the push-in.**
- **Track:** ≈150 BPM (half-time feel), with high-energy percussion onsets every ≈0.25–0.27s.
- **Mix:** loud and compressed (RMS ≈ −10 to −16 dBFS) and very bright (spectral centroid ≈ 6–7.7 kHz: crisp hats, claps and shimmering synths). Energy builds to peaks around 15s and 19s.
- **Ending:** the music is cut off by the hard cut back to the speaker.

---

## Part B: The prompt (Ledger Lens)

> **Create an 18-second vertical (1080×1920, 30fps) product promo for Ledger Lens**, a fintech tool that reads bank statements from any bank, proves every row against the statement's running balance, and answers plain-language questions with the exact rows behind each answer. It uses a sample workspace for a Nigerian lender (Meridian Capital) with GTBank, Access Bank and Moniepoint MFB accounts.

### Global look

- **Stage:** radial spotlight from top centre. `#0a62cf` → `#0749a8` (at 35%) → `#01225b` (at 70%) → `#001232` (corners and bottom), with a soft vignette. No banding.
- **Sting and end-card background:** `#010111`.
- **Captions:** Geist at weight 900, ALL CAPS, `#F4F7FF`, 80px, line-height 0.95, two lines, left-aligned at x=76px. Top captions at y=110px; the "drop" caption sits lower-left at y≈1430px. Words enter one by one, 2 frames apart; each fades in and rises 20px over 7 frames (ease-out cubic). Captions leave by fading over 6 frames.
- **Phone:** 1.7× a 390×844 screen (≈707×1479px), centred horizontally, top at y=360. Graphite bezel, rim light, dynamic island, side buttons. Shadow: `0 60px 120px rgba(0,8,30,.6)`.
- **UI:** the real Ledger Lens app styling (Geist and Geist Mono, cool neutrals, cobalt accent, green for credit and orange-red for debit).
- **Persistent pill** under the phone (from the stage cut until the end card): **"Sample workspace: Meridian Capital"**. White text at 22px on translucent `rgba(150,160,180,.35)` with full rounding, centred at y≈1880.
- **Depth:** perspective 2200px. Tilts are limited to rotateY ±12° and rotateZ ±3–4°. Pop-out elements are rendered unclipped, so they can extend past the phone edges.
- **Never:** gibberish text, flicker, hard camera jerks, more than one caption on screen at a time, or invented numbers. Every figure is a real demo value.

### Shot list (frames at 30fps)

| Frames (s) | Shot | Exact motion | Caption |
|---|---|---|---|
| 0–24 (0–0.8) | **Logo sting** | On `#010111`: the Ledger Lens app icon (white rounded square, lens mark) at 22% frame width. Scales 0.88→1.0 and fades in over frames 0–9 (ease-out), with a blue-white bloom (`0 0 60px rgba(150,190,255,.55)`). Holds | none |
| 24 (0.8) | Hard cut | Cut to the blue stage | none |
| 24–51 (0.8–1.7) | **Phone rise** | Phone with screen off rises from y+1150 to its rest position. rotateZ 6°→3°, rotateY −14°→−8°, scale 0.92→1.0, ease-out cubic | none |
| 51–57 (1.7–1.9) | **Screen wakes** | The Overview dashboard fades in over 6 frames with a faint white flash | none |
| 57–84 (1.9–2.8) | Settle | Phone eases to rotateZ 0°, rotateY 0°, scale 1.0→1.05 | none |
| 84–96 (2.8–3.2) | **Push-in (drop)** | Camera pushes to 1.75×, centred on the "Verified transactions" hero card, over 12 frames with a strong ease-out | none |
| 90–168 (3.0–5.6) | **Hero pop-out** | The navy card lifts out: scale 1.0→1.18, rotateZ 0→−3°, deep shadow. The rest of the screen blurs to 10px and gets a 42% grey wash. The counter ticks 0 → 120 → 141 → 186 as each notification lands | **EVERY STATEMENT. VERIFIED.** (lower-left, from frame 96) |
| 102 / 120 / 138 | **Notifications** | Banners drop from above (spring) into a stack at the top of the frame: "GTBank statement verified / 120 rows match the running balance", "Access Bank statement verified / 21 rows…", "Moniepoint MFB statement verified / 45 rows…". The newest is on top; older ones scale to 0.94 and shift down 16px behind it | (same) |
| 162–186 (5.4–6.2) | **Pull-back** | The card sinks back in, the blur and wash lift, and the camera eases back to 1.0× | caption fades out |
| 186–264 (6.2–8.8) | **Hold: dashboard** | Phone square-on. Slow drift zoom 1.0→1.04. The dashboard scrolls (frames 208–228) to show the detected salary (₦845,000.00, day 25, 6 months) and the risk chips (1 returned item, 6 loan repayments, 13 betting debits) | **EVERY ACCOUNT, AT A GLANCE.** (from frame 192) |
| 264–278 (8.8–9.3) | Transition | In-app push to the Ask screen. The phone tilts to rotateY −12°, rotateZ −3° | swap |
| 278–405 (9.3–13.5) | **Ask** | The question types itself: "How much did I spend at GTBank in July?" (frames 282–314). It sends at 316, the answer lands at 322, and the debit total counts up to ₦480,800.00 by 344. The evidence rows appear at 346. At **352, 358 and 364** three rows pop out (scale 1.15, x offsets −80 / +64 / −64px, shadows), hold, and slide back in at 396–406 | **ASK IT ANYTHING.** (from 270) |
| 405–418 (13.5–13.9) | Transition | Push to the review statement. The tilt flips to rotateY +12°, rotateZ +3° | swap |
| 418–474 (13.9–15.8) | **Proof** | The balance proof shows "Off by ₦500.00". At 424 the misprinted row pops out red (scale 1.12, x −48px). At 448 its amount morphs from ₦6,800.00 to ₦7,300.00 and the border turns green. At 456 the proof reads "Matches" and the badge flips to Reconciled. The row returns at 468 | **EVERY NUMBER, CHECKED.** (from 410) |
| 474–504 (15.8–16.8) | **Bottom sheet** | A statement-summary sheet slides up from the screen bottom (rounded top, grab handle): "Statement reconciled", "26 of 26 rows match the running balance", "Now counts in every answer", and a primary button "View rows". The phone settles to rotateZ −3°, rotateY 0° | **ANSWERS YOU CAN CHECK.** (from 480) |
| 504 (16.8) | Hard cut | Cut to `#010111` | none |
| 504–540 (16.8–18.0) | **End card** | The app icon (scale 0.9→1.0) with the "Ledger Lens" wordmark (Geist 800, 92px, white) beside it and the line "Bank statements you can question." (34px, 70% white) below. The last 6 frames hold | none |

### Sound

- **Track:** original instrumental at **150 BPM, half-time feel**, in B minor / D major (Bm–G–D–A, one chord per bar). It should be bright and punchy: a crisp 16th-note hat pattern with velocity accents, a clap on beat 3 (half-time), a sub kick with an 808-style tail on the root, and bright detuned pluck stabs on the off-beats. Loud but clean master (≈ −12 dBFS RMS, peaks under −1 dBFS) with a bright top end.
- **0–0.8s (sting):** a soft low shimmer and nothing else.
- **0.8–2.8s (phone rise):** near silence plus a rising filtered-noise riser that peaks at 2.8s.
- **2.8s: THE DROP.** Full beat plus an impact (low boom and a short noise burst), timed to the push-in.
- **SFX, tuned to the key and sent to the same reverb as the music:**
  - a two-note notification chime on each banner, each one a step higher;
  - soft whooshes on every camera move and screen push;
  - quiet typing ticks;
  - a bright two-note chime when the answer lands;
  - a soft "pop" on each card pop-out;
  - a low muted tone on "Off by";
  - a rising major chord on "Matches".
- **16.8s:** the music cuts with the hard cut. A single soft bell and a short reverb tail ring under the end card.

### Deliverables

- `brag.mp4` (H.264 + AAC), with frame 0 replaced by the strongest settled frame: the Ask pop-out with the caption fully on screen.
- `brag.jpg`, the poster.
- `share-copy.txt`.
