import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import VoteControl from '@/components/trip/VoteControl';
import { api } from '@/lib/api';

vi.mock('@/lib/api', () => ({ api: vi.fn() }));

const mockApi = vi.mocked(api);

const SAFE_VOTERS = { up_voters: [], down_voters: [] };

beforeEach(() => {
  mockApi.mockReset();
  // Provide a safe default for /voters so hover events from userEvent don't
  // crash the component when the per-test mock doesn't cover that URL.
  mockApi.mockImplementation((url: string) =>
    String(url).endsWith('/voters')
      ? Promise.resolve(SAFE_VOTERS)
      : Promise.resolve(undefined),
  );
});

const tally = (up = 0, down = 0, my_vote = 0) => ({ up, down, my_vote });
const voters = (up: string[] = [], down: string[] = []) => ({
  up_voters: up.map((name) => ({ name })),
  down_voters: down.map((name) => ({ name })),
});

// ── rendering ─────────────────────────────────────────────────────────────────

describe('VoteControl — initial prop', () => {
  it('renders up/down buttons without fetching when initial is supplied', () => {
    render(<VoteControl kind="idea" id={1} canVote initial={tally(3, 1, 0)} />);
    expect(screen.getByLabelText('Upvote')).toBeInTheDocument();
    expect(screen.getByLabelText('Downvote')).toBeInTheDocument();
    expect(mockApi).not.toHaveBeenCalled();
  });

  it('displays initial up and down counts', () => {
    render(<VoteControl kind="idea" id={1} canVote initial={tally(5, 2, 0)} />);
    expect(screen.getByLabelText('Upvote')).toHaveTextContent('5');
    expect(screen.getByLabelText('Downvote')).toHaveTextContent('2');
  });

  it('buttons are enabled when canVote=true and initial is supplied', () => {
    render(<VoteControl kind="idea" id={1} canVote={true} initial={tally(0, 0, 0)} />);
    expect(screen.getByLabelText('Upvote')).not.toBeDisabled();
    expect(screen.getByLabelText('Downvote')).not.toBeDisabled();
  });
});

describe('VoteControl — no initial (fetches from API)', () => {
  it('fetches tally from /api/ideas/:id/votes', async () => {
    mockApi.mockResolvedValue(tally(4, 1, 0));
    render(<VoteControl kind="idea" id={7} canVote />);
    await waitFor(() => expect(mockApi).toHaveBeenCalledWith('/api/ideas/7/votes'));
  });

  it('enables buttons once tally resolves', async () => {
    mockApi.mockResolvedValue(tally(4, 1, 0));
    render(<VoteControl kind="idea" id={7} canVote />);
    await waitFor(() => expect(screen.getByLabelText('Upvote')).not.toBeDisabled());
  });

  it('uses events/ path for kind=event', async () => {
    mockApi.mockResolvedValue(tally(0, 0, 0));
    render(<VoteControl kind="event" id={5} canVote />);
    await waitFor(() => expect(mockApi).toHaveBeenCalledWith('/api/events/5/votes'));
  });
});

// ── canVote=false ─────────────────────────────────────────────────────────────

describe('VoteControl — canVote=false', () => {
  it('disables both buttons', () => {
    render(<VoteControl kind="idea" id={1} canVote={false} initial={tally(0, 0, 0)} />);
    expect(screen.getByLabelText('Upvote')).toBeDisabled();
    expect(screen.getByLabelText('Downvote')).toBeDisabled();
  });

  it('does not call the API when clicked', async () => {
    const user = userEvent.setup();
    render(<VoteControl kind="idea" id={1} canVote={false} initial={tally(0, 0, 0)} />);
    await user.click(screen.getByLabelText('Upvote'));
    expect(mockApi).not.toHaveBeenCalled();
  });
});

// ── casting votes ─────────────────────────────────────────────────────────────

describe('VoteControl — casting votes', () => {
  it('POSTs value 1 when upvoting from neutral', async () => {
    const user = userEvent.setup();
    mockApi.mockImplementation((url: string) =>
      String(url).endsWith('/voters') ? Promise.resolve(SAFE_VOTERS) : Promise.resolve(tally(1, 0, 1)),
    );
    render(<VoteControl kind="idea" id={1} canVote initial={tally(0, 0, 0)} />);

    await user.click(screen.getByLabelText('Upvote'));

    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith('/api/ideas/1/vote', expect.objectContaining({
        method: 'POST',
        json: { value: 1 },
      }))
    );
  });

  it('POSTs value -1 when downvoting from neutral', async () => {
    const user = userEvent.setup();
    mockApi.mockImplementation((url: string) =>
      String(url).endsWith('/voters') ? Promise.resolve(SAFE_VOTERS) : Promise.resolve(tally(0, 1, -1)),
    );
    render(<VoteControl kind="idea" id={1} canVote initial={tally(0, 0, 0)} />);

    await user.click(screen.getByLabelText('Downvote'));

    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith('/api/ideas/1/vote', expect.objectContaining({
        json: { value: -1 },
      }))
    );
  });

  it('POSTs value 0 to toggle off an existing upvote', async () => {
    const user = userEvent.setup();
    mockApi.mockImplementation((url: string) =>
      String(url).endsWith('/voters') ? Promise.resolve(SAFE_VOTERS) : Promise.resolve(tally(0, 0, 0)),
    );
    render(<VoteControl kind="idea" id={1} canVote initial={tally(1, 0, 1)} />);

    await user.click(screen.getByLabelText('Upvote'));

    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith('/api/ideas/1/vote', expect.objectContaining({
        json: { value: 0 },
      }))
    );
  });

  it('optimistically increments the up count before server responds', async () => {
    const user = userEvent.setup();
    let resolveVote!: (v: unknown) => void;
    mockApi.mockImplementation((url: string) => {
      if (String(url).endsWith('/voters')) return Promise.resolve(SAFE_VOTERS);
      return new Promise((r) => { resolveVote = r; });
    });
    render(<VoteControl kind="idea" id={1} canVote initial={tally(2, 0, 0)} />);

    await user.click(screen.getByLabelText('Upvote'));
    // AnimatedCount delays the display by 100ms; waitFor handles that.
    await waitFor(() =>
      expect(screen.getByLabelText('Upvote')).toHaveTextContent('3')
    );
    resolveVote(tally(3, 0, 1));
  });

  it('rolls back to original count on API error', async () => {
    const user = userEvent.setup();
    mockApi.mockImplementation((url: string) => {
      if (String(url).endsWith('/voters')) return Promise.resolve(SAFE_VOTERS);
      return Promise.reject(new Error('network'));
    });
    render(<VoteControl kind="idea" id={1} canVote initial={tally(2, 0, 0)} />);

    await user.click(screen.getByLabelText('Upvote'));

    await waitFor(() =>
      expect(screen.getByLabelText('Upvote')).toHaveTextContent('2')
    );
  });
});

// ── voter popup on hover ──────────────────────────────────────────────────────

describe('VoteControl — voter popup', () => {
  it('fetches voters on hover when tally has votes', async () => {
    mockApi.mockImplementation((url: string) => {
      if (url.endsWith('/voters')) return Promise.resolve(voters(['Alice', 'Bob'], []));
      return Promise.resolve(tally(2, 0, 0));
    });
    render(<VoteControl kind="idea" id={1} canVote initial={tally(2, 0, 0)} />);

    fireEvent.mouseEnter(screen.getByLabelText('Upvote').parentElement!);

    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith('/api/ideas/1/voters')
    );
  });

  it('does not fetch voters on hover when tally is 0/0', () => {
    render(<VoteControl kind="idea" id={1} canVote initial={tally(0, 0, 0)} />);

    fireEvent.mouseEnter(screen.getByLabelText('Upvote').parentElement!);

    expect(mockApi).not.toHaveBeenCalledWith(expect.stringContaining('/voters'));
  });
});
