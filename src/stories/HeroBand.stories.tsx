import type { Meta, StoryObj } from '@storybook/react';
import { HeroBand } from '../components/HeroBand';
import { Button } from '../components/Button';
import { Badge } from '../components/Badge';

const meta: Meta<typeof HeroBand> = { title: 'Hero & Atmospheric/HeroBand', component: HeroBand, parameters: { layout: 'fullscreen' } };
export default meta;
type Story = StoryObj<typeof HeroBand>;

export const Default: Story = {
  args: {
    eyebrow: <Badge>Voice AI platform</Badge>,
    title: 'The most human voice AI',
    subtitle: 'Create lifelike speech, clone voices and deploy conversational agents - in 30 languages, from one platform.',
    actions: (<><Button>Try free</Button><Button variant="outline">Talk to sales</Button></>),
  },
};
export const LeftAligned: Story = {
  args: {
    align: 'left',
    orbs: ['sky', 'rose'],
    title: 'Agents that listen, think and speak',
    subtitle: 'Build real-time voice agents with sub-second latency and natural turn-taking.',
    actions: (<><Button>Build an agent</Button><Button variant="text">See how it works</Button></>),
  },
};
export const Dark: Story = {
  args: {
    dark: true,
    orbs: ['lavender', 'mint'],
    eyebrow: <Badge tone="on-dark">Agents</Badge>,
    title: 'Conversational AI, live in minutes',
    subtitle: 'Voice agents for support, sales and scheduling that sound like your best people.',
    actions: (<><Button onDark>Get started</Button><Button onDark variant="outline">Book a demo</Button></>),
  },
};
