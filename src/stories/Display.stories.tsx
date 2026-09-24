import type { Meta, StoryObj } from '@storybook/react';
import { Display } from '../components/Typography';

const meta: Meta<typeof Display> = { title: 'Foundations/Display', component: Display, args: { children: 'Voices that sound like people' } };
export default meta;
type Story = StoryObj<typeof Display>;

export const Scale: Story = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <Display size="mega">The most human AI voices</Display>
      <Display size="xl">Create lifelike speech</Display>
      <Display size="lg">Built for every story</Display>
      <Display size="md">Agents that listen</Display>
      <Display size="sm">Voice library</Display>
    </div>
  ),
};
export const Mega: Story = { args: { size: 'mega' } };
export const OnDark: Story = {
  args: { size: 'lg', tone: 'on-dark', children: 'Conversational agents, live in minutes' },
  decorators: [(S) => (<div style={{ background: 'var(--cx-color-surface-dark)', padding: 32 }}><S /></div>)],
};
