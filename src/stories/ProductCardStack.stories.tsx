import type { Meta, StoryObj } from '@storybook/react';
import { ProductCard, ProductCardStack } from '../components/ProductCard';
import { GradientOrb } from '../components/GradientOrb';

const meta: Meta<typeof ProductCardStack> = { title: 'Cards/ProductCardStack', component: ProductCardStack, decorators: [(S) => (<div style={{ maxWidth: 400 }}><S /></div>)] };
export default meta;
type Story = StoryObj<typeof ProductCardStack>;

export const Default: Story = {
  render: () => (
    <ProductCardStack>
      <ProductCard media={<GradientOrb color="rose" size={300} />} title="Sound effects" />
      <ProductCard media={<GradientOrb color="mint" size={300} />} title="Dubbing" />
      <ProductCard media={<GradientOrb color="lavender" size={300} />} title="Text to speech" description="Expressive narration in 30 languages." />
    </ProductCardStack>
  ),
};
