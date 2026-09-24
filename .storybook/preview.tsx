import type { Preview } from '@storybook/react';
import { Page } from '../src/components/Layout';
import '../src/styles/index.css';

const preview: Preview = {
  parameters: {
    layout: 'padded',
    backgrounds: { disable: true },
    controls: { expanded: true },
  },
  decorators: [
    (Story) => (
      <Page>
        <Story />
      </Page>
    ),
  ],
};
export default preview;
