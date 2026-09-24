import type { Meta, StoryObj } from '@storybook/react';
import { Text } from '../components/Typography';

const meta: Meta<typeof Text> = { title: 'Foundations/Text', component: Text, args: { children: 'Generate natural speech in 30 languages from a single line of text.' } };
export default meta;
type Story = StoryObj<typeof Text>;

export const Roles: Story = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14, maxWidth: 560 }}>
      <Text variant="caption-uppercase" tone="muted">Text to speech</Text>
      <Text variant="title-md">Studio-quality narration</Text>
      <Text variant="title-sm">Voice design</Text>
      <Text variant="body-md">Turn scripts into expressive audio with fine control over pacing, emotion and emphasis.</Text>
      <Text variant="body-strong">Pay only for the characters you generate.</Text>
      <Text variant="body-sm" tone="muted">Available on every plan, including free.</Text>
      <Text variant="caption" tone="muted">Sample recorded with the "Aria" voice.</Text>
    </div>
  ),
};
export const Body: Story = { args: { variant: 'body-md' } };
export const Muted: Story = { args: { variant: 'body-sm', tone: 'muted' } };
