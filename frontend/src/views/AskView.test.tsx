// @vitest-environment jsdom
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from '../App';
import { StoreProvider, type View } from '../state/store';
import { ApiError, __askFixtureOverrides, __setAskDelay, resetFixtures } from '../api/client';
import type { AskResponse } from '../api/ask.types';
import testDropped from '../api/fixtures/ask/test-dropped.json';
import a01 from '../api/fixtures/ask/a01.json';
import r04 from '../api/fixtures/ask/r04.json';

// Exact strings from backend/ask.yaml -> messages.
const ABSTAIN_NOT_FOUND = "The data room doesn't answer this. No paragraph states it, so there is no figure to give.";
const UNAVAILABLE_LIVE_OFF = 'Free-form questions are switched off in this demo. Try one of the suggested questions.';

function renderApp(view: View = 'ask') {
  const user = userEvent.setup();
  render(
    <StoreProvider initial={{ view }}>
      <App />
    </StoreProvider>,
  );
  return user;
}

const input = () => screen.getByLabelText('Your question') as HTMLTextAreaElement;
const suggestions = () => screen.queryByRole('region', { name: 'Try a suggested question' });
// The submit button (the sidebar also has an "Ask" nav item).
const askButton = () => within(input().closest('form')!).getByRole('button', { name: 'Ask' });
// Visible text only: the polite live region repeats outcomes for screen readers.
const visible = { ignore: '[aria-live], script, style' };
const liveRegion = () => document.querySelector('[role="status"][aria-live="polite"].sr-only')!;

beforeEach(() => {
  resetFixtures();
  __askFixtureOverrides.clear();
  __setAskDelay(20);
  window.location.hash = '';
});
afterEach(() => cleanup());

describe('Ask view', () => {
  it('shows the five suggested questions before the first question', async () => {
    renderApp();
    const list = await screen.findByRole('region', { name: 'Try a suggested question' });
    const buttons = within(list).getAllByRole('button');
    expect(buttons.map((b) => b.textContent)).toEqual([
      'What is the target commercial operation date?',
      'Does the project have rights over every parcel the cable crosses?',
      'Which planning conditions must be discharged before work starts?',
      'Do the documents agree on the export capacity?',
      'How large is the decommissioning bond?',
    ]);
  });

  it('shows a pending state that can be cancelled', async () => {
    __setAskDelay(10_000);
    const user = renderApp();
    await user.click(await screen.findByRole('button', { name: 'What is the target commercial operation date?' }));

    // The question stays visible, submit is disabled, progress is announced politely.
    expect(input().value).toBe('What is the target commercial operation date?');
    expect(askButton()).toHaveAttribute('aria-disabled', 'true');
    expect(screen.getByText('Searching the documents…', visible)).toBeInTheDocument();
    expect(liveRegion()).toHaveTextContent('Searching the documents…');
    expect(await screen.findByText('Checking every quote…', visible, { timeout: 2000 })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    await waitFor(() => expect(screen.queryByText('Checking every quote…', visible)).not.toBeInTheDocument());
    expect(liveRegion()).toHaveTextContent('Question cancelled.');
    expect(input().value).toBe('What is the target commercial operation date?');
    expect(askButton()).toHaveAttribute('aria-disabled', 'false');
  });

  it('answers with citation chips that open the cited passage beside the answer', async () => {
    const user = renderApp();
    await user.click(await screen.findByRole('button', { name: 'Do the documents agree on the export capacity?' }));
    await screen.findByText('Every sentence is backed by an exact quote or a finding');

    expect(screen.getByText('From the asset model')).toBeInTheDocument();
    // The first citation opens automatically; focus stays in the input.
    expect(input()).toHaveFocus();
    expect(liveRegion()).toHaveTextContent('Answer ready: 4 sentences');

    const chip = screen.getByRole('button', { name: 'Open source: Grid connection offer, page 2' });
    expect(chip).toHaveTextContent('Grid offer, p. 2');
    await user.click(chip);
    expect(chip).toHaveAttribute('aria-pressed', 'true');

    const page = screen.getByRole('article', { name: /Grid connection offer, page 2/ });
    const quote = (r04 as AskResponse).sentences[2].citations[0].citation.quote;
    expect(within(page).getByText(quote).tagName).toBe('MARK');
    expect(within(page).getByText('Page 2 of 3')).toBeInTheDocument();
    expect(screen.getByText('Source 3 of 3')).toBeInTheDocument();
  });

  it('opens the finding from a finding chip', async () => {
    const user = renderApp();
    await user.click(await screen.findByRole('button', { name: 'Does the project have rights over every parcel the cable crosses?' }));
    await user.click(await screen.findByRole('button', { name: /^Open Finding 1: No rights for the export cable/ }));
    expect(await screen.findByRole('heading', { level: 1, name: 'No rights for the export cable across Parcels 14 and 15' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Accept' })).toBeInTheDocument();
  });

  it('notes sentences that were removed during verification', async () => {
    __askFixtureOverrides.set('when will the grid connection be made', testDropped as AskResponse);
    const user = renderApp();
    await user.type(input(), 'When will the grid connection be made?{Enter}');
    expect(await screen.findByText("1 sentence was removed because its quote couldn't be verified.")).toBeInTheDocument();
    expect(screen.getByText('Looked up in the documents')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Finding 2: Grid connection falls/ })).toBeInTheDocument(); // Related line
  });

  it('shows an abstention as an answer, not an error, with a route to the seller', async () => {
    const user = renderApp();
    await user.click(await screen.findByRole('button', { name: 'How large is the decommissioning bond?' }));
    expect(await screen.findByText(ABSTAIN_NOT_FOUND, visible)).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Ask the seller instead' }));
    expect(await screen.findByRole('heading', { level: 1, name: /questions for the seller/ })).toBeInTheDocument();
  });

  it('shows the unavailable message and the suggestions for a free-form question', async () => {
    const user = renderApp();
    await screen.findByRole('region', { name: 'Try a suggested question' });
    await user.type(input(), 'Who signed the lease?{Enter}');
    expect(await screen.findByText(UNAVAILABLE_LIVE_OFF, visible)).toBeInTheDocument();
    expect(suggestions()).toBeInTheDocument();
    expect(input().value).toBe('');
  });

  it('shows a scoped error with Retry and keeps the question in the input', async () => {
    let calls = 0;
    __askFixtureOverrides.set('what is the target commercial operation date', () => {
      calls += 1;
      if (calls === 1) throw new ApiError('POST /api/ask failed (503)', 503);
      return a01 as AskResponse;
    });
    const user = renderApp();
    await user.type(input(), 'What is the target commercial operation date?{Enter}');
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent("Couldn't get an answer.");
    expect(alert).toHaveTextContent('Check your connection, then try again.');
    expect(input().value).toBe('What is the target commercial operation date?');

    await user.click(within(alert).getByRole('button', { name: 'Retry' }));
    expect(await screen.findByText(/target commercial operation date of 31 March 2029/)).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('validates 3–500 characters inline and clears the error on edit', async () => {
    const user = renderApp();
    await user.type(input(), 'hi{Enter}');
    expect(input()).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByText('Questions need 3 to 500 characters.')).toBeInTheDocument();
    expect(screen.queryByText('Searching the documents…')).not.toBeInTheDocument();

    await user.type(input(), '!');
    expect(input()).toHaveAttribute('aria-invalid', 'false');
    expect(screen.queryByText('Questions need 3 to 500 characters.')).not.toBeInTheDocument();

    await user.clear(input());
    await user.click(input());
    await user.paste('x'.repeat(501));
    await user.keyboard('{Enter}');
    expect(input()).toHaveAttribute('aria-invalid', 'true');
  });

  it('adds a new line with Shift+Enter instead of submitting', async () => {
    const user = renderApp();
    await user.type(input(), 'Line one{Shift>}{Enter}{/Shift}line two');
    expect(input().value).toBe('Line one\nline two');
    expect(screen.queryByText('Searching the documents…')).not.toBeInTheDocument();
  });

  it('keeps each question in the session history, newest first', async () => {
    const user = renderApp();
    await user.click(await screen.findByRole('button', { name: 'What is the target commercial operation date?' }));
    await screen.findByText(/target commercial operation date of 31 March 2029/, visible);
    await user.type(input(), 'How large is the decommissioning bond?{Enter}');
    await screen.findByText(ABSTAIN_NOT_FOUND, visible);
    const cards = screen.getAllByRole('article', { name: /^Question:/ });
    expect(cards.map((c) => c.getAttribute('aria-label'))).toEqual([
      'Question: How large is the decommissioning bond?',
      'Question: What is the target commercial operation date?',
    ]);
  });
});

describe('Ask keyboard shortcut', () => {
  it('"/" opens Ask and focuses the input from another view, and types normally inside it', async () => {
    const user = renderApp('summary');
    await screen.findByRole('grid', { name: 'Findings' });
    await user.keyboard('/');
    await waitFor(() => expect(input()).toHaveFocus());
    expect(screen.getByRole('heading', { level: 1, name: 'Ask about the data room' })).toBeInTheDocument();

    await user.keyboard('a/b');
    expect(input().value).toBe('a/b');
  });

  it('is listed in the shortcuts sheet', async () => {
    renderApp('summary');
    // The sheet is a native <dialog>; its rows are rendered even while closed.
    expect(await screen.findByText('Ask a question', { selector: 'dt' })).toBeInTheDocument();
  });
});
