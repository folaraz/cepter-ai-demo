import type { Meta, StoryObj } from '@storybook/react';
import { VoiceIcon } from '../components/VoiceIcon';
import { WaveIcon } from './icons';

const meta: Meta<typeof VoiceIcon> = { title: 'Voice Library/VoiceIcon', component: VoiceIcon, args: { initials: 'Ar' } };
export default meta;
type Story = StoryObj<typeof VoiceIcon>;

export const Default: Story = {};
export const Variants: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
      <VoiceIcon initials="Ar" />
      <VoiceIcon icon={<WaveIcon />} />
      <VoiceIcon initials="Th" tone="mint" />
      <VoiceIcon initials="Mi" tone="peach" />
      <VoiceIcon initials="No" tone="lavender" />
      <VoiceIcon initials="Ro" tone="sky" />
      <VoiceIcon initials="Sa" tone="rose" />
      <VoiceIcon initials="Ar" tone="lavender" size={48} />
    </div>
  ),
};
