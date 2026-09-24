import type { Meta, StoryObj } from '@storybook/react';
import { TestimonialCard } from '../components/TestimonialCard';
import { VoiceIcon } from '../components/VoiceIcon';

const meta: Meta<typeof TestimonialCard> = { title: 'Cards/TestimonialCard', component: TestimonialCard, decorators: [(S) => (<div style={{ maxWidth: 520 }}><S /></div>)] };
export default meta;
type Story = StoryObj<typeof TestimonialCard>;

export const Default: Story = {
  args: { quote: '“Our listeners can’t tell which episodes were narrated by a person. That’s the whole point.”', author: 'Maya Okafor', authorRole: 'Head of Audio, Northwind Press', avatar: <VoiceIcon initials="MO" size={40} tone="peach" />, logo: 'NORTHWIND' },
};
export const Minimal: Story = {
  args: { quote: '“Setup took an afternoon. Our support line now answers in eleven languages.”', author: 'Daniel Reyes', authorRole: 'VP Operations' },
};
