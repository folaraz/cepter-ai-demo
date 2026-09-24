import type { Meta, StoryObj } from '@storybook/react';
import { PricingTierCard } from '../components/PricingTierCard';

const meta: Meta<typeof PricingTierCard> = { title: 'Pricing/PricingTierCard', component: PricingTierCard };
export default meta;
type Story = StoryObj<typeof PricingTierCard>;

export const Default: Story = {
  args: { name: 'Starter', price: '$5', period: '/month', description: 'For hobbyists trying voice AI.', features: ['30k characters / month', 'Instant voice cloning', 'Commercial license'], ctaLabel: 'Get started' },
  decorators: [(S) => (<div style={{ maxWidth: 340 }}><S /></div>)],
};
export const Featured: Story = {
  args: { featured: true, badge: 'Most popular', name: 'Creator', price: '$22', period: '/month', description: 'For creators publishing every week.', features: ['100k characters / month', 'Professional voice cloning', '192 kbps audio', 'Usage-based overage'], ctaLabel: 'Start free trial' },
  decorators: [(S) => (<div style={{ maxWidth: 340 }}><S /></div>)],
};
export const Tiers: Story = {
  render: () => (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, alignItems: 'stretch' }}>
      <PricingTierCard name="Free" price="$0" period="/month" description="Explore the platform." features={['10k characters / month', '3 custom voices']} ctaLabel="Sign up" />
      <PricingTierCard featured badge="Most popular" name="Creator" price="$22" period="/month" description="For weekly publishers." features={['100k characters / month', 'Professional cloning', '192 kbps audio']} ctaLabel="Start free trial" />
      <PricingTierCard name="Enterprise" price="Custom" description="Security, scale and support." features={['Volume pricing', 'SSO & audit logs', 'Dedicated support']} ctaLabel="Contact sales" />
    </div>
  ),
};
