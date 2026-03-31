# Design System — veng.dev

## Product Context
- **What this is:** Marketing landing page + docs site for vibe-engineer, a CLI tool for documentation-driven development
- **Who it's for:** Engineers who already know what vibe coding is
- **Space/industry:** Developer tools, AI-assisted coding
- **Project type:** Marketing site evolving into documentation site

## Aesthetic Direction
- **Direction:** Industrial/Utilitarian
- **Decoration level:** Minimal. Typography does all the work. No gradients, no blobs, no decorative elements. The code blocks ARE the decoration.
- **Mood:** An engineer's artifact that happens to be a website. Serious about craft, never corporate. Feels like a beautifully formatted README rendered as a web page.
- **Reference sites:** max.cloud (data-dense, engineer-to-engineer tone), Astro.build (dark-first, code-forward), Linear.app (restrained motion)

## Typography
- **Display/Hero:** Geist, 600 weight — clean geometric sans. Not overused outside Vercel's ecosystem. Pairs naturally with the mono variant.
- **Body:** Geist, 400 weight — same family, lighter weight for body. Keeps it cohesive.
- **UI/Labels:** Geist Mono, 11px uppercase with 0.08em letter-spacing for card labels and section markers.
- **Data/Tables:** Geist Mono, 400 weight — supports tabular-nums, designed alongside Geist.
- **Code:** Geist Mono, 400 weight — beautiful ligatures, designed together with Geist.
- **Loading:** Google Fonts CDN: `family=Geist:wght@300;400;500;600;700&family=Geist+Mono:wght@400;500`
- **Scale:**
  - Hero tagline: 48px / 600 weight / -0.02em tracking / 1.1 line-height
  - H2: 32px / 600 weight / -0.01em tracking / 1.2 line-height
  - H3: 24px / 500 weight / 1.3 line-height
  - Lead: 18px / 400 weight / 1.7 line-height
  - Body: 16px / 400 weight / 1.7 line-height
  - Small: 14px / 400 weight / 1.6 line-height
  - Code: 13px / 400 weight / 1.7 line-height
  - Label: 11px / uppercase / 0.08em tracking

## Color

### Dark Mode (default)
- **Approach:** Restrained. One accent + neutrals. Color is rare and meaningful.
- **Background:** `#0a0a0b` — near-black, slightly warm
- **Surface:** `#141416` — subtle lift for code blocks
- **Surface highlight:** `#1a1d14` — dark olive tint for decision record cards
- **Border:** `#222225` — subtle separation
- **Primary text:** `#e8e8e6` — warm off-white, not pure white
- **Muted text:** `#8b8b8b` — secondary content, captions
- **Accent:** `#e07a3a` — warm amber/orange. Deliberate departure from blue/purple convention. Evokes terminal cursors and caution lights. Used for: backreference comments, tagline emphasis, card borders, link hover states.

### Light Mode
- **Background:** `#fafaf9`
- **Surface:** `#f0f0ee`
- **Surface highlight:** `#eef0e8`
- **Border:** `#dddddd`
- **Primary text:** `#1a1a1a`
- **Muted text:** `#6b6b6b`
- **Accent:** `#c06020` — same amber family, darkened for contrast on light backgrounds

### Syntax Highlighting
- Comment: `#6a9955` (dark) / `#008000` (light)
- String: `#ce9178` (dark) / `#a31515` (light)
- Keyword: `#569cd6` (dark) / `#0000ff` (light)
- Function: `#dcdcaa` (dark) / `#795e26` (light)
- Class: `#4ec9b0` (dark) / `#267f99` (light)
- Number: `#b5cea8` (dark) / `#098658` (light)
- Backreference: `#e07a3a` at 0.85 opacity — accent color, slightly muted to avoid overwhelming the code

### Semantic Colors
- Success: `#4ade80`
- Warning: `#e07a3a` (same as accent, intentional)
- Error: `#ef4444`
- Info: `#60a5fa`

## Spacing
- **Base unit:** 4px
- **Density:** Comfortable. Not cramped, not airy.
- **Scale:** 2xs(2px) xs(4px) sm(8px) md(16px) lg(24px) xl(32px) 2xl(48px) 3xl(64px) 4xl(96px)
- **Between elements:** 16px
- **Between sub-sections:** 48px
- **Between major sections:** 96px

## Layout
- **Approach:** Grid-disciplined. Centered, single-column.
- **Max content width (prose):** 720px — narrower than convention, reads like a blog post
- **Max content width (code):** 840px — code needs more horizontal room
- **Grid:** Single column, no sidebar on landing page. Docs pages use left sidebar.
- **Border radius:** sm: 3px (inline code), md: 6px (buttons, tabs), lg: 8px (code blocks, cards)
- **Nav:** Minimal top bar. Logo "ve" in Geist Mono on left. Links (Docs, GitHub, dark mode toggle) on right. 16px vertical padding.

## Motion
- **Approach:** Minimal-functional. Content is the show.
- **Easing:** ease-out for entrances, ease-in for exits
- **Duration:** micro(100ms) for toggles, short(200ms) for scroll reveals
- **Code blocks:** Fade in on scroll (200ms ease-out)
- **Dark mode toggle:** Instant (no transition on theme switch)
- **Everything else:** No motion. Static.

## Component Patterns

### Code Block
- Background: surface color
- Border: 1px solid border color
- Border radius: 8px
- Padding: 24px
- Font: Geist Mono 13px
- Overflow: horizontal scroll on mobile

### Decision Record Card
- Background: surface-highlight color
- Left border: 3px solid accent
- Border radius: 0 8px 8px 0
- Padding: 24px 28px
- Label: Geist Mono 11px uppercase, accent color

### CTA Install Block
- Tabbed (uv default, pip alternate)
- Tab bar: 1px border, 6px radius
- Command: Geist Mono 16px, surface background, 16px 32px padding

### Badge
- Geist Mono 11px
- 1px border, 4px border-radius
- Muted text color

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-30 | Initial design system created | Created by /design-consultation based on competitive research of dev tool landing pages (max.cloud, Astro.build, Linear.app, Evil Martians study of 100+ dev tool pages) |
| 2026-03-30 | Amber accent (#e07a3a) over blue/purple | Deliberate departure from every dev tool in the space. Evokes terminal cursors, instantly recognizable. |
| 2026-03-30 | 720px max-width for prose | Narrower than convention. Reads like a README, not a marketing page. More intimate, better readability. |
| 2026-03-30 | Code-only hero (no illustration) | Code with backreferences IS the product. Engineers read code. The page respects that. |
| 2026-03-30 | Geist + Geist Mono | Designed as a pair. Clean, geometric, not overused outside Vercel. Mono variant has excellent ligatures for code samples. |
