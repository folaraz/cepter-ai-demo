import type { Meta, StoryObj } from '@storybook/react';
import { VoiceRow } from '../components/VoiceRow';
import { Button } from '../components/Button';
import { Badge } from '../components/Badge';
import { PlayIcon } from './icons';

const meta: Meta<typeof VoiceRow> = { title: 'Voice Library/VoiceRow', component: VoiceRow, decorators: [(S) => (<div style={{ maxWidth: 720 }}><S /></div>)] };
export default meta;
type Story = StoryObj<typeof VoiceRow>;

export const Default: Story = {
  args: { name: 'Aria', accent: 'American · Warm, conversational', initials: 'Ar', action: <Button variant="outline" size="sm" leadingIcon={<PlayIcon />}>Preview</Button> },
};
export const List: Story = {
  render: () => (
    <div>
      <VoiceRow name="Aria" accent="American · Warm, conversational" initials="Ar" iconTone="lavender" tags={<><Badge shape="tag">Narration</Badge><Badge shape="tag">Female</Badge></>} action={<Button variant="outline" size="sm">Preview</Button>} />
      <VoiceRow name="Theo" accent="British · Deep documentary" initials="Th" iconTone="mint" tags={<><Badge shape="tag">Documentary</Badge><Badge shape="tag">Male</Badge></>} action={<Button variant="outline" size="sm">Preview</Button>} selected />
      <VoiceRow name="Lucía" accent="Spanish · Bright, upbeat" initials="Lu" iconTone="peach" tags={<><Badge shape="tag">Ads</Badge><Badge shape="tag">Female</Badge></>} action={<Button variant="outline" size="sm">Preview</Button>} />
      <VoiceRow name="Kenji" accent="Japanese · Calm support" initials="Ke" iconTone="sky" tags={<><Badge shape="tag">Agents</Badge><Badge shape="tag">Male</Badge></>} action={<Button variant="outline" size="sm">Preview</Button>} />
    </div>
  ),
};
