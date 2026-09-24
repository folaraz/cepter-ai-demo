import type { Meta, StoryObj } from '@storybook/react';
import { FooterLink } from '../components/Footer';

const meta: Meta<typeof FooterLink> = { title: 'CTA & Footer/FooterLink', component: FooterLink, args: { children: 'Text to speech' } };
export default meta;
type Story = StoryObj<typeof FooterLink>;

export const Default: Story = {};
export const Column: Story = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <FooterLink>Privacy</FooterLink><FooterLink>Terms</FooterLink><FooterLink>Safety</FooterLink>
    </div>
  ),
};
