---
name: Inheritors Senior Digital Care
colors:
  surface: '#fcf9f8'
  surface-dim: '#dcd9d9'
  surface-bright: '#fcf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f2'
  surface-container: '#f0eded'
  surface-container-high: '#eae7e7'
  surface-container-highest: '#e5e2e1'
  on-surface: '#1c1b1b'
  on-surface-variant: '#5a3f46'
  inverse-surface: '#313030'
  inverse-on-surface: '#f3f0ef'
  outline: '#8e6f76'
  outline-variant: '#e2bdc5'
  surface-tint: '#ba005c'
  primary: '#b6005a'
  on-primary: '#ffffff'
  primary-container: '#e01572'
  on-primary-container: '#fffbff'
  inverse-primary: '#ffb1c5'
  secondary: '#885200'
  on-secondary: '#ffffff'
  secondary-container: '#fe9d00'
  on-secondary-container: '#663c00'
  tertiary: '#67585f'
  on-tertiary: '#ffffff'
  tertiary-container: '#807077'
  on-tertiary-container: '#fffbff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffd9e1'
  primary-fixed-dim: '#ffb1c5'
  on-primary-fixed: '#3f001b'
  on-primary-fixed-variant: '#8f0045'
  secondary-fixed: '#ffdcbb'
  secondary-fixed-dim: '#ffb869'
  on-secondary-fixed: '#2c1700'
  on-secondary-fixed-variant: '#673d00'
  tertiary-fixed: '#f2dde5'
  tertiary-fixed-dim: '#d5c1c9'
  on-tertiary-fixed: '#23181e'
  on-tertiary-fixed-variant: '#514349'
  background: '#fcf9f8'
  on-background: '#1c1b1b'
  surface-variant: '#e5e2e1'
typography:
  headline-lg:
    fontFamily: Be Vietnam Pro
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 44px
  headline-lg-mobile:
    fontFamily: Be Vietnam Pro
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 38px
  headline-md:
    fontFamily: Be Vietnam Pro
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 34px
  body-lg:
    fontFamily: Noto Sans KR
    fontSize: 20px
    fontWeight: '500'
    lineHeight: 30px
  body-md:
    fontFamily: Noto Sans KR
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  label-lg:
    fontFamily: Noto Sans KR
    fontSize: 16px
    fontWeight: '700'
    lineHeight: 24px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Noto Sans KR
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  container-padding: 24px
  gutter: 16px
  touch-target-min: 56px
  stack-gap-lg: 32px
  stack-gap-md: 20px
---

## Brand & Style

The brand identity focuses on reliability, warmth, and accessibility for a senior demographic. It leverages the "Neuri" character mascot to lower the barrier to complex legal and inheritance topics. 

The design style is **Corporate Modern with a Soft Edge**, prioritizing clarity and trust. It utilizes high-contrast elements and generous whitespace to ensure legibility. The interface avoids complex gestures or small interactive zones, opting for a physical-first digital metaphor where elements look and feel stable and easy to interact with. The mood is supportive and professional, yet approachable through the vibrant pink accent and friendly mascot illustrations.

## Colors

The palette is anchored by a vibrant **Primary Pink (#F52D81)**, used strategically for the main call-to-action buttons, active navigation states, and critical highlights. This color provides the necessary visual weight to guide the user's eye.

- **Background:** A clean off-white (#F9F9F9) reduces eye strain compared to pure white while maintaining high contrast with text.
- **Surface:** Pure white is used for card containers and input fields to create subtle depth.
- **Secondary/Accent:** The orange from the "Neuri" character is used sparingly for informational icons or secondary status indicators.
- **Functional:** Success, Warning, and Error colors follow standard patterns but are adjusted for high visibility.

## Typography

Typography is the most critical accessibility tool in this design system. We use **Noto Sans KR** for its exceptional legibility and wide range of weights.

- **Scale:** Font sizes start at a minimum of 18px for body text to ensure readability for users with presbyopia. 
- **Weight:** Medium and Bold weights are preferred over regular or thin weights to maintain high stroke visibility.
- **Spacing:** Line heights are set generously (1.5x minimum) to prevent lines of text from blurring together.
- **Hierarchy:** Use the Primary Pink for specific keywords within body text to highlight important legal terms or actions.

## Layout & Spacing

The layout follows a **Fluid Grid** model with strict margin requirements to prevent content from touching the screen edges.

- **Safe Zones:** A 24px side margin is mandatory on all mobile screens.
- **Touch Targets:** Every interactive element (buttons, toggles, links) must have a minimum touch target height of 56px.
- **Vertical Rhythm:** A large 32px gap is used between major sections to clearly separate concepts.
- **Consistency:** All spacing is based on an 8px scale.
- **Desktop/Tablet:** On larger screens, content is centered within a 720px max-width container to prevent long line lengths that are difficult for seniors to scan.

## Elevation & Depth

This design system uses **Tonal Layering** combined with **Low-Contrast Outlines** rather than heavy shadows, which can sometimes appear "blurry" or "dirty" to older eyes.

- **Z-0:** Background (#F9F9F9).
- **Z-1:** Cards and Containers. These use a 1px solid border (#E0E0E0) to define their boundaries clearly against the background.
- **Z-2:** Floating elements or active modals. These use a soft, large-radius ambient shadow with 5% opacity to indicate they are "above" the current context.
- **Interaction:** Buttons use a subtle inner-glow or darker border on press to provide immediate physical feedback.

## Shapes

The shape language is **Rounded**, conveying friendliness and safety. 

- **Standard Elements:** Buttons and input fields use a 0.5rem (8px) radius.
- **Large Containers:** Cards and image containers (like the mascot frame) use a 1rem (16px) radius.
- **Special Elements:** Chat bubbles for the user use a "Pill" style on three corners with a sharper corner on the right to indicate direction.

## Components

### Buttons
Primary buttons use the #F52D81 background with white text. They must always include a right-pointing arrow icon to signal "progress." Secondary buttons use a white background with a 2px pink border.

### Input Fields
Inputs must have a thick 2px border when focused. Placeholder text should be high-contrast (at least 4.5:1 ratio) to ensure users can read instructions before typing.

### Cards
Cards are the primary container for information. They feature a light pink (#FDE8F0) background when they contain the "Neuri" mascot or helpful tips to distinguish them from standard neutral content.

### Chat Interface
- **Bot/Neuri Bubble:** Light grey or soft pink background, left-aligned with the mascot avatar.
- **User Bubble:** Solid Primary Pink background with white text, right-aligned.
- **Text Controls:** Include "Text Size Up" and "Text Size Down" buttons at the top of long legal documents or chat flows.

### Chips & Tags
Used for quick-reply suggestions in the chatbot. These should be large, easy to tap, and use the Secondary Orange or Primary Pink for the border to indicate they are interactive.