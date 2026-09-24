import type { Meta, StoryObj } from '@storybook/react';
import { Footer } from '../components/Footer';

const columns = [
  { title: 'Products', links: [{ label: 'Text to speech' }, { label: 'Voice cloning' }, { label: 'Dubbing' }, { label: 'Agents' }] },
  { title: 'Solutions', links: [{ label: 'Publishing' }, { label: 'Gaming' }, { label: 'Support' }] },
  { title: 'Developers', links: [{ label: 'API' }, { label: 'Docs' }, { label: 'Status' }] },
  { title: 'Company', links: [{ label: 'About' }, { label: 'Careers' }, { label: 'Blog' }] },
  { title: 'Legal', links: [{ label: 'Privacy' }, { label: 'Terms' }, { label: 'Safety' }] },
];

const meta: Meta<typeof Footer> = { title: 'CTA & Footer/Footer', component: Footer, parameters: { layout: 'fullscreen' } };
export default meta;
type Story = StoryObj<typeof Footer>;

export const Default: Story = { args: { tagline: 'Voice AI that sounds like people.', columns, legal: '© 2026 cepter ai demo', bottomRight: 'English (US)' } };
export const Compact: Story = { args: { columns: columns.slice(0, 3), legal: '© 2026 cepter ai demo' } };
