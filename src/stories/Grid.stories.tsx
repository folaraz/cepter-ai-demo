import type { Meta, StoryObj } from '@storybook/react';
import { Grid } from '../components/Layout';
import { FeatureCard } from '../components/FeatureCard';

const meta: Meta<typeof Grid> = { title: 'Layout/Grid', component: Grid };
export default meta;
type Story = StoryObj<typeof Grid>;

export const TwoUp: Story = {
  render: () => (
    <Grid columns={2}>
      <FeatureCard title="Creative platform" description="Narration, dubbing, music and sound effects." />
      <FeatureCard title="Agents platform" description="Voice agents with tools, memory and analytics." />
    </Grid>
  ),
};
export const ThreeUp: Story = {
  render: () => (
    <Grid columns={3} gap="base">
      <FeatureCard title="Low latency" description="Streaming speech in under 100ms." />
      <FeatureCard title="Any language" description="30 languages, one voice." />
      <FeatureCard title="Secure" description="SOC 2, GDPR and SSO." />
    </Grid>
  ),
};
