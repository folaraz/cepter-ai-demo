import type { Meta, StoryObj } from '@storybook/react';
import { GradientOrb } from '../components/GradientOrb';

const meta: Meta<typeof GradientOrb> = { title: 'Hero & Atmospheric/GradientOrb', component: GradientOrb };
export default meta;
type Story = StoryObj<typeof GradientOrb>;

export const Palette: Story = {
  render: () => (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
      {(['mint', 'peach', 'lavender', 'sky', 'rose'] as const).map((c) => (
        <div key={c} style={{ position: 'relative', overflow: 'hidden', height: 180, background: 'var(--cx-color-canvas-soft)', borderRadius: 16 }}>
          <GradientOrb color={c} size={200} />
          <span style={{ position: 'absolute', left: 12, bottom: 10, zIndex: 1, fontSize: 12, fontWeight: 600, letterSpacing: 0.96, textTransform: 'uppercase', color: 'var(--cx-color-ink)' }}>{c}</span>
        </div>
      ))}
    </div>
  ),
};
export const Atmosphere: Story = {
  render: () => (
    <div style={{ position: 'relative', overflow: 'hidden', height: 320, background: 'var(--cx-color-canvas)', borderRadius: 24 }}>
      <GradientOrb color="lavender" size={380} x="40%" y="45%" />
      <GradientOrb color="mint" size={300} x="65%" y="60%" />
      <GradientOrb color="peach" size={260} x="25%" y="70%" />
    </div>
  ),
};
