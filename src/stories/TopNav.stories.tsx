import type { Meta, StoryObj } from '@storybook/react';
import { TopNav } from '../components/TopNav';
import { Button } from '../components/Button';

const links = [{ label: 'Creative', active: true }, { label: 'Agents' }, { label: 'Video' }, { label: 'Pricing' }, { label: 'Enterprise' }, { label: 'Docs' }];

const meta: Meta<typeof TopNav> = { title: 'Navigation/TopNav', component: TopNav, parameters: { layout: 'fullscreen' } };
export default meta;
type Story = StoryObj<typeof TopNav>;

export const Default: Story = {
  args: { links, actions: (<><Button variant="text" size="sm" style={{ textDecoration: 'none' }}>Sign in</Button><Button size="sm">Try free</Button></>) },
};
export const Bordered: Story = { args: { ...Default.args, bordered: true } };
export const Dark: Story = {
  args: { tone: 'dark', links, actions: (<><Button onDark variant="text" size="sm" style={{ textDecoration: 'none' }}>Sign in</Button><Button onDark size="sm">Try free</Button></>) },
};
