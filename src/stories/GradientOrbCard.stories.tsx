import type { Meta, StoryObj } from '@storybook/react';
import { GradientOrbCard } from '../components/GradientOrbCard';
import { Badge } from '../components/Badge';
import { Button } from '../components/Button';

const meta: Meta<typeof GradientOrbCard> = { title: 'Hero & Atmospheric/GradientOrbCard', component: GradientOrbCard };
export default meta;
type Story = StoryObj<typeof GradientOrbCard>;

export const Default: Story = {
  args: { tone: 'lavender', eyebrow: <Badge>Text to speech</Badge>, title: 'Stories that sound alive', description: 'Expressive narration for audiobooks, video and games.', footer: <Button variant="outline" size="sm">Listen</Button> },
  decorators: [(S) => (<div style={{ maxWidth: 480 }}><S /></div>)],
};
export const AllTones: Story = {
  render: () => (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
      <GradientOrbCard tone="mint" title="Dubbing" description="Translate video while keeping the original voice." minHeight={260} />
      <GradientOrbCard tone="peach" title="Voice cloning" description="A faithful digital twin from one minute of audio." minHeight={260} />
      <GradientOrbCard tone="sky" title="Agents" description="Real-time conversation with natural turn-taking." minHeight={260} />
      <GradientOrbCard tone="rose" title="Sound effects" description="Describe a sound; hear it seconds later." minHeight={260} />
      <GradientOrbCard tone="lavender" title="Music" description="Studio-grade tracks from a text prompt." minHeight={260} />
    </div>
  ),
};
