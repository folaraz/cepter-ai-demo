import type { Meta, StoryObj } from '@storybook/react';
import { TextInput } from '../components/TextInput';
import { SearchIcon } from './icons';

const meta: Meta<typeof TextInput> = { title: 'Forms & Tags/TextInput', component: TextInput, args: { label: 'Work email', placeholder: 'you@company.com' }, decorators: [(S) => (<div style={{ maxWidth: 360 }}><S /></div>)] };
export default meta;
type Story = StoryObj<typeof TextInput>;

export const Default: Story = {};
export const WithHint: Story = { args: { hint: "We'll send your API key here." } };
export const Error: Story = { args: { defaultValue: 'alex@', error: 'Enter a valid email address.' } };
export const Search: Story = { args: { label: undefined, placeholder: 'Search 5,000+ voices', icon: <SearchIcon /> } };
