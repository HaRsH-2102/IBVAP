---
name: Tactical Intelligence Interface
colors:
  surface: '#111318'
  surface-dim: '#111318'
  surface-bright: '#37393e'
  surface-container-lowest: '#0c0e12'
  surface-container-low: '#1a1c20'
  surface-container: '#1e2024'
  surface-container-high: '#282a2e'
  surface-container-highest: '#333539'
  on-surface: '#e2e2e8'
  on-surface-variant: '#c2c6d6'
  inverse-surface: '#e2e2e8'
  inverse-on-surface: '#2f3035'
  outline: '#8c909f'
  outline-variant: '#424754'
  surface-tint: '#adc6ff'
  primary: '#adc6ff'
  on-primary: '#002e6a'
  primary-container: '#4d8eff'
  on-primary-container: '#00285d'
  inverse-primary: '#005ac2'
  secondary: '#4edea3'
  on-secondary: '#003824'
  secondary-container: '#00a572'
  on-secondary-container: '#00311f'
  tertiary: '#ffb786'
  on-tertiary: '#502400'
  tertiary-container: '#df7412'
  on-tertiary-container: '#461f00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#004395'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#ffdcc6'
  tertiary-fixed-dim: '#ffb786'
  on-tertiary-fixed: '#311400'
  on-tertiary-fixed-variant: '#723600'
  background: '#111318'
  on-background: '#e2e2e8'
  surface-variant: '#333539'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-base:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  data-mono:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: -0.01em
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '700'
    lineHeight: 12px
    letterSpacing: 0.06em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  container-padding: 16px
  element-gap: 8px
  grid-gutter: 12px
---

## Brand & Style

The design system is engineered for high-stakes, 24/7 mission control environments. It employs a **Modern Technical** style with elements of **Minimalism** and **Tactile Utility**. The focus is on cognitive load reduction through extreme clarity and functional aesthetics.

The visual language communicates authority and precision. It avoids all decorative flourishes in favor of structural integrity. Surfaces use subtle depth to distinguish between monitoring layers, while the "Severity Color System" provides the only vibrant visual cues, ensuring that operator attention is immediately directed to anomalies. The interface should feel like a high-performance tool: cold, responsive, and indestructible.

## Colors

The palette is anchored in a "Deep Night" spectrum to minimize eye strain during long shifts. 

- **Base Surfaces:** The primary background uses `#0A0C10`. All container elements use `#151921` to create a logical separation from the base.
- **Accents & Severity:** Use these colors exclusively for status indicators, data highlights, and alerts. Do not use severity colors for decorative elements.
- **Interactions:** The primary Blue (`#3B82F6`) is used for active states, selections, and focus indicators.
- **Borders:** All UI boundaries use a consistent `#262C36` border to maintain structure without creating high-contrast visual noise.

## Typography

This design system uses a dual-font strategy to separate UI navigation from technical data.

1.  **Inter:** Used for all interface chrome, headings, and standard body text. It provides high legibility at small scales.
2.  **JetBrains Mono:** Reserved for "hard data." Use this for GPS coordinates, timestamps, IP addresses, object IDs, and forensic logs. The monospaced nature ensures that changing numerical values do not cause layout "jitter."

**Hierarchy Rule:** Use `label-caps` for all table headers and small metadata descriptors to maintain a technical, "instrument panel" feel.

## Layout & Spacing

The layout utilizes a **High-Density Fluid Grid**. Efficiency of space is the primary requirement.

- **Grid:** A 12-column layout for the main workspace, with a fixed 280px sidebar for navigation/filters.
- **Information Density:** Use tight spacing (`4px` and `8px` increments) to maximize the amount of data visible on a single screen without scrolling.
- **Margins:** Standard outer margin of `16px`. Internal card padding should be `12px` to keep content compact.
- **Video Grids:** Use a specific `2px` gap between video feeds to provide maximum screen real estate to the video content while maintaining a clear frame separation.

## Elevation & Depth

This system avoids traditional shadows in favor of **Tonal Layering** and **Structural Outlines**.

- **Z-Index 0 (Background):** `#0A0C10` (The base "desk").
- **Z-Index 1 (Panels):** `#151921` with a `1px solid #262C36` border. This is the standard container for data and video.
- **Z-Index 2 (Popovers/Tooltips):** `#1C222B` with a subtle `4px` blur shadow (Opacity 40%) to suggest it is floating above the workspace.
- **Interactive Depth:** On hover, clickable cards should brighten their border to `#3B82F6` rather than lifting with a shadow. This maintains the "flat-panel" aesthetic favored in command centers.

## Shapes

The shape language is **Soft-Angular**. 

- **Standard Radius:** `4px` (`rounded-sm`). This provides a slight hint of modernization while maintaining the rigid, professional structure of a military-grade application.
- **Video Feeds:** Should remain strictly square (`0px`) to maximize pixel usage for the analytics overlay.
- **Badges:** Use a `2px` radius for status tags to differentiate them from functional buttons.

## Components

### Buttons & Controls
- **Primary:** Solid `#3B82F6` with white text.
- **Ghost/Technical:** Transparent background with `#262C36` borders. Used for secondary actions in data tables.
- **Icon Buttons:** Strictly 32x32px or 24x24px to maintain density.

### Technical Data Cards
Cards should have a header area using `label-caps` for the title. Body content should prioritize `data-mono` for metrics. Use a left-aligned colored border (2px width) to indicate the severity status of the data within the card.

### Video Containers
Video feeds must support an "Overlays" layer. Analytics boxes (bounding boxes) should use `1px` stroke widths in the color corresponding to the alert level. 

### Severity Badges
Small, rectangular tags with low-opacity backgrounds (15% of the hex color) and high-contrast text. Example: A "Critical" badge is `#EF4444` text on a dark red-tinted background.

### Timeline/Forensic Rail
The timeline component uses a horizontal axis with `JetBrains Mono` for time markers. Key events are marked with vertical pips color-coded by severity.