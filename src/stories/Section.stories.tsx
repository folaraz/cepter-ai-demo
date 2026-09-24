import type { Meta, StoryObj } from '@storybook/react';
import { Section, Grid } from '../components/Layout';
import { Display, Text } from '../components/Typography';
import { FeatureCard } from '../components/FeatureCard';

const meta: Meta<typeof Section> = { title: 'Layout/Section', component: Section, parameters: { layout: 'fullscreen' } };
export default meta;
type Story = StoryObj<typeof Section>;

export const Default: Story = {
  render: () => (
    <Section>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 32 }}>
        <Text variant="caption-uppercase" tone="muted">Platform</Text>
        <Display size="lg">Everything you need to ship voice</Display>
      </div>
      <Grid columns={3}>
        <FeatureCard title="Text to speech" description="Lifelike narration in 30 languages." />
        <FeatureCard title="Voice cloning" description="A digital twin from one minute of audio." />
        <FeatureCard title="Agents" description="Real-time conversation over phone and web." />
      </Grid>
    </Section>
  ),
};
export const Dark: Story = {
  render: () => (
    <Section tone="dark" compact>
      <Display size="lg">Enterprise-grade voice</Display>
      <Text style={{ marginTop: 12 }} tone="on-dark-soft">SOC 2 Type II, GDPR, data residency and SSO.</Text>
    </Section>
  ),
};
