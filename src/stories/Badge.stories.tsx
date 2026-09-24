import type { Meta, StoryObj } from '@storybook/react';
import { Badge } from '../components/Badge';

const meta: Meta<typeof Badge> = { title: 'Forms & Tags/Badge', component: Badge, args: { children: 'New' } };
export default meta;
type Story = StoryObj<typeof Badge>;

export const Default: Story = {};
export const Tones: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
      <Badge>Text to speech</Badge>
      <Badge tone="outline">Beta</Badge>
      <Badge tone="ink">Most popular</Badge>
      <Badge dot="success">Live</Badge>
      <span style={{ background: 'var(--cx-color-surface-dark)', padding: 8, borderRadius: 999 }}><Badge tone="on-dark">Enterprise</Badge></span>
    </div>
  ),
};
export const Tags: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: 6 }}>
      <Badge shape="tag">Narration</Badge>
      <Badge shape="tag">Calm</Badge>
      <Badge shape="tag" tone="outline">British</Badge>
    </div>
  ),
};
