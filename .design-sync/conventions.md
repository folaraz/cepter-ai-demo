# cepter-ui - how to build with it

An editorial, print-magazine look for a voice-AI product: off-white canvas, warm near-black ink, light serif headlines, soft pastel "orbs" as the only colour. Every component is on `window.CepterUI`.

## Wrap every screen in `<Page>`
`Page` sets the canvas background (`--cx-color-canvas`), Inter body type with +0.16px tracking, and `box-sizing`. Without it, your own layout glue falls back to browser defaults (the components themselves still style correctly).

```jsx
const { Page, TopNav, HeroBand, Section, Grid, FeatureCard, CtaBand, Footer, Button, Badge, Display, Text } = window.CepterUI;

<Page>
  <TopNav links={[{ label: 'Creative', active: true }, { label: 'Agents' }, { label: 'Pricing' }]}
          actions={<><Button variant="text" size="sm">Sign in</Button><Button size="sm">Try free</Button></>} />
  <HeroBand eyebrow={<Badge>Voice AI platform</Badge>} title="The most human voice AI"
            subtitle="Lifelike speech and real-time agents in 30 languages."
            actions={<><Button>Try free</Button><Button variant="outline">Talk to sales</Button></>} />
  <Section tone="soft">
    <Text variant="caption-uppercase" tone="muted">Platform</Text>
    <Display size="lg" style={{ margin: '12px 0 32px' }}>Built for every story</Display>
    <Grid columns={3}>
      <FeatureCard title="Text to speech" description="Expressive narration in 30 languages." />
    </Grid>
  </Section>
  <CtaBand title="Start creating today" actions={<Button>Try free</Button>} orb="mint" />
</Page>
```

## Layout vocabulary
- `Section` = full-width band with the 96px section rhythm, content capped at 1200px. `tone`: `canvas` | `soft` | `card` | `dark`; `compact` gives 48px.
- `Grid columns={2|3|4}` = responsive card grid (3/4 -> 2 -> 1). `Container` = the 1200px column on its own.
- Spacing tokens (4px base): `--cx-space-xxs` 4, `-xs` 8, `-sm` 12, `-base` 16, `-md` 20, `-lg` 24, `-xl` 32, `-xxl` 48, `-section` 96.

## Styling idiom: `--cx-*` CSS variables + `cx-*` type classes
Use the tokens for any custom styling. Never hard-code hex values.
- Colour: `--cx-color-canvas`, `-canvas-soft`, `-surface-card`, `-surface-strong`, `-surface-dark`, `-ink`, `-body`, `-muted`, `-muted-soft`, `-hairline`, `-hairline-strong`, `-primary`, `-on-dark`, `-on-dark-soft`, `-success`, `-error`.
- Atmosphere only: `--cx-gradient-mint|peach|lavender|sky|rose`. Use them through `<GradientOrb>`, `GradientOrbCard tone`, `HeroBand orbs`, `CtaBand orb`, and `VoiceIcon tone`. Never as a button fill, text colour or card background.
- Radius: `--cx-radius-md` 8 (inputs), `-lg` 12, `-xl` 16 (cards), `-xxl` 24 (orb cards), `-pill` (buttons, badges).
- Type: `<Display size="mega|xl|lg|md|sm">` (serif, weight 300 - never bold it) and `<Text variant="title-md|title-sm|body-md|body-strong|body-sm|caption|caption-uppercase" tone="ink|body|muted|on-dark|on-dark-soft">`. The same roles exist as classes: `cx-display-lg`, `cx-body-md`, `cx-caption-uppercase`, … plus `cx-tone-muted` etc.
- Fonts: `--cx-font-display` (Newsreader, standing in for Waldenburg Light) and `--cx-font-body` (Inter).

## Rules
- One `Button variant="primary"` (ink pill) per view. The secondary action is `variant="outline"`, and inline links are `variant="text"`. On dark bands, pass `onDark`.
- Dark surfaces: `Section tone="dark"`, `HeroBand dark`, `CtaBand dark`, `TopNav tone="dark"`, `PricingTierCard featured`.
- Voice lists: stack `VoiceRow`s directly; the hairline dividers are built in. Put `Badge shape="tag"` in `tags` and a small outline `Button` in `action`.

## Where the truth lives
`styles.css` (and its `_ds_bundle.css` import) holds every token and class. Each `components/<group>/<Name>/<Name>.prompt.md` and `.d.ts` lists the exact props.
