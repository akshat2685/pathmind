---
name: Living Sketchbook
colors:
  surface: '#fdfae7'
  surface-dim: '#dddbc8'
  surface-bright: '#fdfae7'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f7f4e1'
  surface-container: '#f1eedb'
  surface-container-high: '#ece9d6'
  surface-container-highest: '#e6e3d0'
  on-surface: '#1c1c11'
  on-surface-variant: '#424842'
  inverse-surface: '#313124'
  inverse-on-surface: '#f4f1de'
  outline: '#737972'
  outline-variant: '#c2c8c0'
  surface-tint: '#4a654e'
  primary: '#4a654e'
  on-primary: '#ffffff'
  primary-container: '#8ba88e'
  on-primary-container: '#233d29'
  inverse-primary: '#b0ceb2'
  secondary: '#7d562d'
  on-secondary: '#ffffff'
  secondary-container: '#ffca98'
  on-secondary-container: '#7a532a'
  tertiary: '#8b4c50'
  on-tertiary: '#ffffff'
  tertiary-container: '#d88d90'
  on-tertiary-container: '#5d272b'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#cceace'
  primary-fixed-dim: '#b0ceb2'
  on-primary-fixed: '#07200f'
  on-primary-fixed-variant: '#334d38'
  secondary-fixed: '#ffdcbd'
  secondary-fixed-dim: '#f0bd8b'
  on-secondary-fixed: '#2c1600'
  on-secondary-fixed-variant: '#623f18'
  tertiary-fixed: '#ffdada'
  tertiary-fixed-dim: '#ffb3b5'
  on-tertiary-fixed: '#380b10'
  on-tertiary-fixed-variant: '#6f3539'
  background: '#fdfae7'
  on-background: '#1c1c11'
  surface-variant: '#e6e3d0'
typography:
  headline-lg:
    fontFamily: Bricolage Grotesque
    fontSize: 48px
    fontWeight: '600'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Bricolage Grotesque
    fontSize: 32px
    fontWeight: '500'
    lineHeight: 40px
  headline-sm:
    fontFamily: Bricolage Grotesque
    fontSize: 24px
    fontWeight: '500'
    lineHeight: 32px
  body-lg:
    fontFamily: Source Serif 4
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Source Serif 4
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Be Vietnam Pro
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.05em
  note-handwritten:
    fontFamily: Bricolage Grotesque
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 24px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  margin-page: 40px
  gutter-organic: 24px
  safe-area: 32px
---

## Brand & Style
The brand personality is rooted in the "Path" concept—an organic, evolving journey of knowledge. It avoids the cold, clinical efficiency of traditional AI in favor of a **Tactile / Minimalist** aesthetic that mimics a physical academic journal. The goal is to evoke mindfulness and intellectual curiosity, reducing the friction of learning through soft textures and human-centric imperfection. 

The visual direction rejects rigid digital patterns for a "living sketchbook" feel, where the UI appears to be hand-sketched on parchment. It prioritizes the emotional state of the learner, providing a calm, encouraging environment that feels personal, permanent, and private.

## Colors
The palette is physiologically grounded to reduce eye strain and promote focus. 
- **Primary (Sage Green):** Represents growth and stability. Used for progress and primary actions.
- **Secondary (Muted Ochre):** Evokes old paper and academic heritage. Used for highlights and search states.
- **Tertiary (Dusty Rose):** A soft accent for interactive elements or gentle nudges.
- **Neutral (Parchment Cream):** The base surface, providing a warm, non-reflective background.
- **Text (Espresso):** Deep, warm charcoal-brown replaces harsh blacks to maintain the analog ink feel.

Watercolor textures should be applied as subtle overlays on container backgrounds to create depth and variation.

## Typography
The system uses a pairing of a characterful, expressive sans-serif and a sturdy, academic serif.
- **Headlines:** Use **Bricolage Grotesque** for its quirky, hand-cut feel. It mimics high-quality handwriting without sacrificing legibility.
- **Body:** Use **Source Serif 4** for long-form learning content. Its classic proportions ensure readability during deep focus sessions.
- **Labels:** **Be Vietnam Pro** provides a clean, contemporary contrast for functional UI metadata.

Use "note-handwritten" for annotations, marginalia, and agent-led encouragements to simulate a personal tutor writing in the margins of your book.

## Layout & Spacing
This system rejects the "card-heavy" grid in favor of a **Contextual Fluid Layout**. 
- **The Path Model:** Content flows vertically like a scroll or an unfolding map. Elements should have varied horizontal alignments (slightly offset from the center) to avoid a rigid digital appearance.
- **Negative Space:** Use generous margins (40px+) to allow the "parchment" to breathe. 
- **Reflow:** On mobile, the "Path" collapses into a single, centered column with increased vertical breathing room between "learning nodes."

## Elevation & Depth
Depth is created through **Tactile Layering** rather than traditional shadows.
- **Shadows:** Use very soft, multi-layered "ink-bleed" shadows. These are low-opacity, spread wide, and tinted with the Espresso text color (`rgba(61, 52, 48, 0.08)`).
- **Physicality:** Elements should appear to "sit" on the paper. Use subtle 1px inner borders that mimic the slight indentation of a letterpress or a pencil stroke.
- **Watercolor Blurs:** Higher elevation levels use a soft, colored backdrop blur that mimics a wet watercolor wash behind the active container.

## Shapes
Shapes are intentionally imperfect. 
- Use **Asymmetrical Roundedness**: Instead of perfect `16px` corners, apply varying radii (e.g., `18px 14px 20px 12px`) to containers to simulate hand-drawn paper.
- **Pencil Borders:** Strokes should not be perfectly solid. Use a slightly textured SVG mask or a CSS border-image that mimics a graphite line or a fountain pen stroke.
- **Organic Blobs:** Background decorative elements use soft, fluid "blob" shapes that represent the "living" nature of the learning path.

## Components
- **Buttons:** Styled as hand-stamped elements. The "primary" button uses a Sage Green watercolor fill with a slightly irregular border. Hover states should trigger a "soak" effect where the color deepens as if the paper is absorbing ink.
- **Learning Nodes (Cards):** These are the core units of "Path." They feature a torn-paper edge on the bottom and a subtle grain texture.
- **Input Fields:** Styled as a single horizontal "pencil line" that expands slightly when focused. 
- **Chips/Tags:** Appear as small pieces of "washi tape" with low-opacity colors and a subtle adhesive texture.
- **Progress Indicators:** A "Living Vine" or ink-line that grows as the user completes tasks, avoiding standard percentage bars.
- **Icons:** Must be hand-drawn, monoline strokes with slight overshoots at the corners to maintain the sketchbook aesthetic.