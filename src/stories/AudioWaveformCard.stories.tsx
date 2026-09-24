import type { Meta, StoryObj } from '@storybook/react';
import { AudioWaveformCard } from '../components/AudioWaveformCard';
import { VoiceIcon } from '../components/VoiceIcon';
import { Badge } from '../components/Badge';

const meta: Meta<typeof AudioWaveformCard> = { title: 'Hero & Atmospheric/AudioWaveformCard', component: AudioWaveformCard, decorators: [(S) => (<div style={{ maxWidth: 420 }}><S /></div>)] };
export default meta;
type Story = StoryObj<typeof AudioWaveformCard>;

export const Default: Story = {
  args: { voiceName: 'Aria', detail: 'American · Warm narration', icon: <VoiceIcon initials="Ar" size={40} tone="lavender" />, duration: '0:42', seed: 3 },
};
export const Playing: Story = {
  args: { voiceName: 'Theo', detail: 'British · Documentary', icon: <VoiceIcon initials="Th" size={40} tone="mint" />, duration: '1:08', progress: 0.45, playing: true, seed: 11,
    tags: (<><Badge shape="tag">Calm</Badge><Badge shape="tag">Deep</Badge></>) },
};
