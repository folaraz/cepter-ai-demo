import type { Meta, StoryObj } from '@storybook/react';
import { ProductCard } from '../components/ProductCard';
import { GradientOrb } from '../components/GradientOrb';
import { AudioWaveformCard } from '../components/AudioWaveformCard';
import { VoiceIcon } from '../components/VoiceIcon';

const meta: Meta<typeof ProductCard> = { title: 'Cards/ProductCard', component: ProductCard, decorators: [(S) => (<div style={{ maxWidth: 400 }}><S /></div>)] };
export default meta;
type Story = StoryObj<typeof ProductCard>;

export const Default: Story = {
  args: {
    media: (<><GradientOrb color="sky" size={320} /><div style={{ position: 'relative', zIndex: 1, width: '78%' }}><AudioWaveformCard voiceName="Nova" detail="Support agent" icon={<VoiceIcon initials="No" tone="sky" />} duration="0:18" seed={5} bars={32} /></div></>),
    title: 'Conversational agents',
    description: 'Answer calls, book meetings and resolve tickets in real time.',
  },
};
export const MediaOnly: Story = {
  args: { media: (<GradientOrb color="peach" size={360} />), mediaAspect: '4 / 3' },
};
