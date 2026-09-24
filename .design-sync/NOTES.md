# design-sync notes - cepter-ui

- Source spec: `design-system/design-system.md` (editorial voice-AI style guide). The library was built from it. Brand text is "cepter ai demo"; there are no third-party names or logos.
- [GENERAL] Display font: the spec's Waldenburg is licensed, and its suggested EB Garamond has no 300 weight. Newsreader (variable, 200-800, OFL) is used at 300. Font files are vendored in `src/fonts/`, and `scripts/build-css.mjs` copies them into `dist/fonts/`.
- [GENERAL] `dist/styles.css` = fonts + tokens + base type + component CSS, assembled by `scripts/build-css.mjs` after tsup. `cfg.cssEntry` points at it.
- [GENERAL] The `.storybook/preview.tsx` decorator can't be bundled by the converter (it imports CSS that pulls in `.woff2`). `cfg.provider = {component: "Page"}` replaces it, and the Storybook decorator also wraps in `<Page>`, so both sides match.
- TopNav: overflowed between 768 and ~1000px, so it now collapses to a hamburger below 960px. Captured at `viewport 1280x240` so the full menu is verified.
- ProductCardStack: transformed back cards were painting over the untransformed front card. Fixed with explicit z-index plus `transform-origin: top`.
- Page: captured at `1280x1400` (single-card mode) so the whole landing composition is compared.
- `cardMode: column` for Button, FeatureCard, Footer, TopNav, PricingTierCard, VoiceIcon (from `[GRID_OVERFLOW]`).
- The default compare viewport is ~900px wide, so grids render 2-up and Footer uses its tablet layout on both panels. That's expected.

## Re-sync risks
- Rebuild `.design-sync/sb-reference` whenever component CSS or stories change. The reference is what grades compare against.
- `cfg.provider` = Page: if Page ever gains required props or context, previews change silently.
- The Newsreader substitution is a stand-in. If a licensed Waldenburg arrives, swap `src/styles/fonts.css` + `--cx-font-display` and re-verify every component that shows display type.
- Toolchain at first sync: Storybook 8.6, React 18.3, tsup 8, Node 22.
