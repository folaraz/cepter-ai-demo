import type { Meta, StoryObj } from '@storybook/react';
import { FeatureCard } from '../components/FeatureCard';
import { Button } from '../components/Button';
import { MicIcon, GlobeIcon, BotIcon, ArrowRight } from './icons';

const meta: Meta<typeof FeatureCard> = { title: 'Cards/FeatureCard', component: FeatureCard };
export default meta;
type Story = StoryObj<typeof FeatureCard>;

export const Default: Story = {
  args: { icon: <MicIcon />, title: 'Voice cloning', description: 'Create a faithful digital twin of any voice from a short sample.', footer: <Button variant="text" trailingIcon={<ArrowRight />}>Learn more</Button> },
  decorators: [(S) => (<div style={{ maxWidth: 360 }}><S /></div>)],
};
export const Grid: Story = {
  render: () => (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
      <FeatureCard icon={<MicIcon />} title="Text to speech" description="Lifelike narration with control over emotion and pacing." />
      <FeatureCard icon={<GlobeIcon />} title="30 languages" description="Switch languages mid-sentence without losing the voice." />
      <FeatureCard icon={<BotIcon />} title="Voice agents" description="Deploy real-time agents to phone, web and apps." interactive />
    </div>
  ),
};
