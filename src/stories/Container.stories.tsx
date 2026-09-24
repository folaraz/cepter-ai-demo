import type { Meta, StoryObj } from '@storybook/react';
import { Container } from '../components/Layout';
import { Text } from '../components/Typography';

const meta: Meta<typeof Container> = { title: 'Layout/Container', component: Container, parameters: { layout: 'fullscreen' } };
export default meta;
type Story = StoryObj<typeof Container>;

export const Default: Story = {
  render: () => (
    <Container>
      <div style={{ border: '1px dashed var(--cx-color-hairline-strong)', borderRadius: 12, padding: 24 }}>
        <Text>Content is capped at 1200px with 24px gutters.</Text>
      </div>
    </Container>
  ),
};
