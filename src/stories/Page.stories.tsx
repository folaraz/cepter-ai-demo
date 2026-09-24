import type { Meta, StoryObj } from '@storybook/react';
import { Page, Section, Grid } from '../components/Layout';
import { TopNav } from '../components/TopNav';
import { HeroBand } from '../components/HeroBand';
import { Button } from '../components/Button';
import { Badge } from '../components/Badge';
import { FeatureCard } from '../components/FeatureCard';
import { CtaBand } from '../components/CtaBand';
import { Display } from '../components/Typography';
import { MicIcon, GlobeIcon, BotIcon } from './icons';

const meta: Meta<typeof Page> = { title: 'Layout/Page', component: Page, parameters: { layout: 'fullscreen' } };
export default meta;
type Story = StoryObj<typeof Page>;

export const Landing: Story = {
  render: () => (
    <Page>
      <TopNav links={[{ label: 'Creative' }, { label: 'Agents' }, { label: 'Pricing' }, { label: 'Docs' }]} actions={<Button size="sm">Try free</Button>} />
      <HeroBand eyebrow={<Badge>Voice AI platform</Badge>} title="The most human voice AI" subtitle="Lifelike speech and real-time agents in 30 languages." actions={<><Button>Try free</Button><Button variant="outline">Talk to sales</Button></>} />
      <Section tone="soft">
        <Display size="lg" style={{ marginBottom: 32 }}>Built for every story</Display>
        <Grid columns={3}>
          <FeatureCard icon={<MicIcon />} title="Text to speech" description="Expressive narration with control over emotion." />
          <FeatureCard icon={<GlobeIcon />} title="Dubbing" description="Translate video and keep the original voice." />
          <FeatureCard icon={<BotIcon />} title="Agents" description="Voice agents for phone, web and apps." />
        </Grid>
      </Section>
      <CtaBand title="Start creating today" actions={<Button>Try free</Button>} orb="mint" />
    </Page>
  ),
};
