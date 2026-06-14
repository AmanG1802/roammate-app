import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import BrainstormChat from '@/components/trip/BrainstormChat';
import { api } from '@/lib/api';
import { useEntitlement } from '@/hooks/useEntitlement';

// ── module mocks ──────────────────────────────────────────────────────────────

vi.mock('@/lib/api', () => {
  class ApiError extends Error {
    status: number;
    data: unknown;
    constructor(status: number, message: string, data: unknown = null) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
      this.data = data;
    }
  }
  return { api: vi.fn(), ApiError };
});

vi.mock('@/hooks/useEntitlement', () => ({
  useEntitlement: vi.fn(),
  isNeedsPlus: vi.fn(() => null),
}));

vi.mock('@/components/billing/QuotaPill', () => ({
  BrainstormQuotaPill: () => <div data-testid="quota-pill" />,
}));

vi.mock('@/components/common/VoiceInputButton', () => ({
  default: () => <button aria-label="Voice input" />,
}));

// render markdown as plain text so we can assert on content
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => <span>{children}</span>,
}));

vi.mock('framer-motion', () => import('../helpers/framerMock'));

// ── test helpers ──────────────────────────────────────────────────────────────

const mockApi = vi.mocked(api);
const mockUseEntitlement = vi.mocked(useEntitlement);

function makeEntitlement(overrides: {
  brainstorm_remaining?: number | null;
  requirePlus?: ReturnType<typeof vi.fn>;
} = {}) {
  return {
    entitlement: {
      tier: 'free' as const,
      brainstorm_remaining: overrides.brainstorm_remaining ?? 15,
    },
    isLoading: false,
    isConfirmed: true,
    refresh: vi.fn().mockResolvedValue(undefined),
    requirePlus: overrides.requirePlus ?? vi.fn().mockResolvedValue(false),
    pendingPaywall: null,
    resolvePaywall: vi.fn(),
  };
}

const msg = (
  id: number,
  role: 'user' | 'assistant',
  content: string,
  created_at = '2024-01-01T10:00:00Z',
) => ({ id, role, content, created_at });

beforeEach(() => {
  mockApi.mockReset();
  mockUseEntitlement.mockReturnValue(makeEntitlement() as ReturnType<typeof useEntitlement>);
});

// ── loading messages ──────────────────────────────────────────────────────────

describe('BrainstormChat — load messages', () => {
  it('loads and renders chat history on mount', async () => {
    mockApi.mockResolvedValue([
      msg(1, 'user', 'Where should I go in Paris?'),
      msg(2, 'assistant', 'Try the Louvre!'),
    ]);

    render(<BrainstormChat tripId="42" onItemsCreated={vi.fn()} />);

    await waitFor(() =>
      expect(screen.getByText('Where should I go in Paris?')).toBeInTheDocument()
    );
    expect(screen.getByText('Try the Louvre!')).toBeInTheDocument();
    expect(mockApi).toHaveBeenCalledWith(
      '/api/trips/42/brainstorm/messages',
      expect.objectContaining({ cache: 'no-store' }),
    );
  });

  it('shows empty state when there are no messages', async () => {
    mockApi.mockResolvedValue([]);
    render(<BrainstormChat tripId="1" onItemsCreated={vi.fn()} />);
    expect(await screen.findByText(/Start brainstorming/i)).toBeInTheDocument();
  });

  it('shows load error banner when the initial fetch fails', async () => {
    mockApi.mockRejectedValue(new Error('network'));
    render(<BrainstormChat tripId="1" onItemsCreated={vi.fn()} />);
    expect(await screen.findByText(/Couldn't load chat history/i)).toBeInTheDocument();
  });

  it('retries loading when the Retry link in the error banner is clicked', async () => {
    const user = userEvent.setup();
    mockApi
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValue([msg(1, 'user', 'Hello')]);

    render(<BrainstormChat tripId="1" onItemsCreated={vi.fn()} />);
    await screen.findByText(/Couldn't load chat history/i);

    await user.click(screen.getByRole('button', { name: /Retry/i }));
    await waitFor(() => expect(screen.getByText('Hello')).toBeInTheDocument());
  });
});

// ── send message ──────────────────────────────────────────────────────────────

describe('BrainstormChat — sending messages', () => {
  it('shows an optimistic user bubble immediately after send', async () => {
    const user = userEvent.setup();
    let resolveChat!: (v: unknown) => void;
    mockApi
      .mockResolvedValueOnce([]) // initial load
      .mockReturnValueOnce(new Promise((r) => { resolveChat = r; }));

    render(<BrainstormChat tripId="1" onItemsCreated={vi.fn()} />);
    await screen.findByText(/Start brainstorming/i);

    await user.type(screen.getByRole('textbox'), 'Best spots in Rome?');
    await user.click(screen.getByLabelText('Send message'));

    expect(screen.getByText('Best spots in Rome?')).toBeInTheDocument();
    resolveChat({ history: [msg(1, 'user', 'Best spots in Rome?'), msg(2, 'assistant', 'Try the Colosseum!')] });
  });

  it('appends the assistant reply after the server responds', async () => {
    const user = userEvent.setup();
    mockApi
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce({
        history: [
          msg(1, 'user', 'Hello?'),
          msg(2, 'assistant', 'Hi there!'),
        ],
      });

    render(<BrainstormChat tripId="1" onItemsCreated={vi.fn()} />);
    await screen.findByText(/Start brainstorming/i);

    await user.type(screen.getByRole('textbox'), 'Hello?');
    await user.click(screen.getByLabelText('Send message'));

    await waitFor(() => expect(screen.getByText('Hi there!')).toBeInTheDocument());
  });

  it('sends on Enter key press (not Shift+Enter)', async () => {
    const user = userEvent.setup();
    mockApi
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce({ history: [msg(1, 'user', 'Go!'), msg(2, 'assistant', 'Sure!')] });

    render(<BrainstormChat tripId="1" onItemsCreated={vi.fn()} />);
    await screen.findByText(/Start brainstorming/i);

    await user.type(screen.getByRole('textbox'), 'Go!{Enter}');

    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith(
        '/api/trips/1/brainstorm/chat',
        expect.objectContaining({ method: 'POST', json: { message: 'Go!' } }),
      )
    );
  });

  it('clears the input after a successful send', async () => {
    const user = userEvent.setup();
    mockApi
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce({ history: [msg(1, 'user', 'hi'), msg(2, 'assistant', 'hello')] });

    render(<BrainstormChat tripId="1" onItemsCreated={vi.fn()} />);
    await screen.findByText(/Start brainstorming/i);

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'hi');
    await user.click(screen.getByLabelText('Send message'));

    await waitFor(() => expect((textarea as HTMLTextAreaElement).value).toBe(''));
  });

  it('does not send when input is empty', async () => {
    const user = userEvent.setup();
    mockApi.mockResolvedValue([]);

    render(<BrainstormChat tripId="1" onItemsCreated={vi.fn()} />);
    await screen.findByText(/Start brainstorming/i);

    const sendBtn = screen.getByLabelText('Send message');
    expect(sendBtn).toBeDisabled();
    await user.click(sendBtn);
    expect(mockApi).toHaveBeenCalledTimes(1); // only the initial load
  });
});

// ── failed message ────────────────────────────────────────────────────────────

describe('BrainstormChat — failed message', () => {
  it('shows an error bubble when the AI response fails', async () => {
    const user = userEvent.setup();
    mockApi
      .mockResolvedValueOnce([])
      .mockRejectedValueOnce(new Error('timeout'));

    render(<BrainstormChat tripId="1" onItemsCreated={vi.fn()} />);
    await screen.findByText(/Start brainstorming/i);

    await user.type(screen.getByRole('textbox'), 'Will this fail?');
    await user.click(screen.getByLabelText('Send message'));

    await waitFor(() =>
      expect(screen.getByText(/Couldn't get a response/i)).toBeInTheDocument()
    );
  });

  it('retries the failed message when Retry is clicked', async () => {
    const user = userEvent.setup();
    mockApi
      .mockResolvedValueOnce([])
      .mockRejectedValueOnce(new Error('timeout'))
      .mockResolvedValueOnce({ history: [msg(1, 'user', 'Test'), msg(2, 'assistant', 'OK!')] });

    render(<BrainstormChat tripId="1" onItemsCreated={vi.fn()} />);
    await screen.findByText(/Start brainstorming/i);

    await user.type(screen.getByRole('textbox'), 'Test');
    await user.click(screen.getByLabelText('Send message'));

    await screen.findByText(/Couldn't get a response/i);
    await user.click(screen.getByRole('button', { name: /Retry/i }));

    await waitFor(() => expect(screen.getByText('OK!')).toBeInTheDocument());
  });
});

// ── "Create items from chat" button ──────────────────────────────────────────

describe('BrainstormChat — extract button', () => {
  it('shows "Create items from chat" only after an assistant reply exists', async () => {
    mockApi.mockResolvedValue([
      msg(1, 'user', 'Hello?'),
      msg(2, 'assistant', 'Here are some ideas!'),
    ]);
    render(<BrainstormChat tripId="1" onItemsCreated={vi.fn()} />);
    await waitFor(() =>
      expect(screen.getByText(/Create items from chat/i)).toBeInTheDocument()
    );
  });

  it('is absent when there are no assistant messages', async () => {
    mockApi.mockResolvedValue([]);
    render(<BrainstormChat tripId="1" onItemsCreated={vi.fn()} />);
    await screen.findByText(/Start brainstorming/i);
    expect(screen.queryByText(/Create items from chat/i)).not.toBeInTheDocument();
  });

  it('POSTs to /brainstorm/extract and calls onItemsCreated', async () => {
    const user = userEvent.setup();
    const onItemsCreated = vi.fn();
    mockApi.mockImplementation((url: string) => {
      if (url.endsWith('/messages')) {
        return Promise.resolve([msg(1, 'user', 'Hi'), msg(2, 'assistant', 'Ideas!')]);
      }
      return Promise.resolve(undefined);
    });

    render(<BrainstormChat tripId="7" onItemsCreated={onItemsCreated} />);
    await waitFor(() => expect(screen.getByText(/Create items from chat/i)).toBeInTheDocument());

    await user.click(screen.getByText(/Create items from chat/i));

    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith(
        '/api/trips/7/brainstorm/extract',
        expect.objectContaining({ method: 'POST' }),
      )
    );
    expect(onItemsCreated).toHaveBeenCalled();
  });
});

// ── quota exhausted ───────────────────────────────────────────────────────────

describe('BrainstormChat — quota exhausted', () => {
  it('disables the textarea and shows a lock button when quota is 0', async () => {
    mockUseEntitlement.mockReturnValue(
      makeEntitlement({ brainstorm_remaining: 0 }) as ReturnType<typeof useEntitlement>
    );
    mockApi.mockResolvedValue([]);

    render(<BrainstormChat tripId="1" onItemsCreated={vi.fn()} />);
    await screen.findByText(/Start brainstorming/i);

    const textarea = screen.getByRole('textbox');
    expect(textarea).toBeDisabled();
    expect(textarea).toHaveAttribute('placeholder', 'Out of free brainstorms');
    expect(screen.getByLabelText('Get Plus to keep chatting')).toBeInTheDocument();
  });

  it('calls requirePlus when the lock button is clicked', async () => {
    const user = userEvent.setup();
    const requirePlus = vi.fn().mockResolvedValue(false);
    mockUseEntitlement.mockReturnValue(
      makeEntitlement({ brainstorm_remaining: 0, requirePlus }) as ReturnType<typeof useEntitlement>
    );
    mockApi.mockResolvedValue([]);

    render(<BrainstormChat tripId="1" onItemsCreated={vi.fn()} />);
    await screen.findByText(/Start brainstorming/i);

    await user.click(screen.getByLabelText('Get Plus to keep chatting'));
    expect(requirePlus).toHaveBeenCalledWith('brainstorm_quota');
  });
});
