// @vitest-environment jsdom
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { StoreProvider } from '../state/store';
import { DatesCard } from './DatesCard';
import { RequestsView } from './RequestsView';
import type { Summary } from '../api/types';
import summaryFixture from '../api/fixtures/summary.json';

afterEach(cleanup);

const summary = summaryFixture as Summary;

describe('Critical dates', () => {
  it('shows the clash and the long-horizon row when their checks flag', () => {
    render(
      <StoreProvider>
        <DatesCard summary={summary} />
      </StoreProvider>,
    );
    expect(screen.getByRole('button', { name: /Grid connects 184 days after target COD/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /After 2030/ })).toBeInTheDocument();
  });

  it('hides them when the API sends null (the checks passed)', () => {
    render(
      <StoreProvider>
        <DatesCard summary={{ ...summary, clash: null, long_horizon: null }} />
      </StoreProvider>,
    );
    expect(screen.queryByRole('button', { name: /days after target COD/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /After 2030/ })).not.toBeInTheDocument();
    // The dates themselves still render.
    expect(screen.getByRole('button', { name: /Grid connection/ })).toBeInTheDocument();
  });
});

describe('Requests', () => {
  it('says so when there is nothing to ask the seller', () => {
    render(
      <StoreProvider initial={{ view: 'rfi', rfi: { status: 'ready', data: [] } }}>
        <RequestsView />
      </StoreProvider>,
    );
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('No questions for the seller.');
    expect(
      screen.getByText('No open requests: every check either passed or rests on facts already in the data room.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Download questions/ })).toHaveAttribute('aria-disabled', 'true');
    expect(screen.queryByRole('list')).not.toBeInTheDocument();
  });
});
