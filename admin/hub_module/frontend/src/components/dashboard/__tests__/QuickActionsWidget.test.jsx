import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import QuickActionsWidget from '../QuickActionsWidget';

const wrap = (id) => (
  <MemoryRouter>
    <QuickActionsWidget id={id} />
  </MemoryRouter>
);

describe('QuickActionsWidget', () => {
  it('renders the card header', () => {
    render(wrap('comm-1'));
    expect(screen.getByText('Quick Actions')).toBeInTheDocument();
  });

  it('renders Submit Support Ticket link', () => {
    render(wrap('comm-1'));
    expect(screen.getByText('Submit Support Ticket')).toBeInTheDocument();
  });

  it('renders My Support Tickets link', () => {
    render(wrap('comm-1'));
    expect(screen.getByText('My Support Tickets')).toBeInTheDocument();
  });

  it('submit link href includes community id', () => {
    render(wrap('abc123'));
    const link = screen.getByText('Submit Support Ticket').closest('a');
    expect(link).toHaveAttribute('href', '/community/abc123/support/submit');
  });

  it('my tickets link href includes community id', () => {
    render(wrap('abc123'));
    const link = screen.getByText('My Support Tickets').closest('a');
    expect(link).toHaveAttribute('href', '/community/abc123/support/my-tickets');
  });
});
