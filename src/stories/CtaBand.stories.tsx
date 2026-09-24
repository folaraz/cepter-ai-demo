import type { Meta, StoryObj } from '@storybook/react';
import { CtaBand } from '../components/CtaBand';
import { Button } from '../components/Button';

const meta: Meta<typeof CtaBand> = { title: 'CTA & Footer/CtaBand', component: CtaBand, parameters: { layout: 'fullscreen' } };
export default meta;
type Story = StoryObj<typeof CtaBand>;

export const Default: Story = {
  args: { title: 'Start creating with the most human voices', subtitle: 'Free to try. No credit card required.', actions: <Button>Try free</Button>, orb: 'peach' },
};
export const Dark: Story = {
  args: { dark: true, title: 'Ready to put an agent on the phone?', actions: (<><Button onDark>Build an agent</Button><Button onDark variant="outline">Talk to sales</Button></>), orb: 'lavender' },
};
