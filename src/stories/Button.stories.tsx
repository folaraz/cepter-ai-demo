import type { Meta, StoryObj } from '@storybook/react';
import { Button } from '../components/Button';
import { ArrowRight, PlayIcon } from './icons';

const meta: Meta<typeof Button> = { title: 'Actions/Button', component: Button, args: { children: 'Try free' } };
export default meta;
type Story = StoryObj<typeof Button>;

export const Primary: Story = { args: { variant: 'primary' } };
export const Outline: Story = { args: { variant: 'outline', children: 'Contact sales' } };
export const Text: Story = { args: { variant: 'text', children: 'Read the docs', trailingIcon: <ArrowRight /> } };
export const Sizes: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
      <Button size="sm">Small</Button>
      <Button>Medium</Button>
      <Button size="lg">Large</Button>
      <Button variant="outline" leadingIcon={<PlayIcon />}>Play sample</Button>
      <Button disabled>Disabled</Button>
    </div>
  ),
};
export const OnDark: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: 12, background: 'var(--cx-color-surface-dark)', padding: 24, borderRadius: 16 }}>
      <Button onDark>Get started</Button>
      <Button onDark variant="outline">Book a demo</Button>
    </div>
  ),
};
