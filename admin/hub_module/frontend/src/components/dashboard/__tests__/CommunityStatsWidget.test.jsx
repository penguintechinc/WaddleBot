import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import CommunityStatsWidget from '../CommunityStatsWidget';

describe('CommunityStatsWidget', () => {
  it('renders all three stat labels', () => {
    render(<CommunityStatsWidget community={{ memberCount: 100 }} recentActivity={[]} streams={[]} />);
    expect(screen.getByText('Members')).toBeInTheDocument();
    expect(screen.getByText('Live Streams')).toBeInTheDocument();
    expect(screen.getByText('Recent Activity')).toBeInTheDocument();
  });

  it('formats member count with locale string', () => {
    render(<CommunityStatsWidget community={{ memberCount: 1234 }} recentActivity={[]} streams={[]} />);
    expect(screen.getByText('1,234')).toBeInTheDocument();
  });

  it('shows em-dash when community is null', () => {
    render(<CommunityStatsWidget community={null} recentActivity={[]} streams={[]} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('shows em-dash when memberCount is undefined', () => {
    render(<CommunityStatsWidget community={{}} recentActivity={[]} streams={[]} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('counts live streams from streams array length', () => {
    render(<CommunityStatsWidget community={null} recentActivity={[]} streams={[{}, {}, {}]} />);
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('shows 0 for streams when streams is empty', () => {
    render(<CommunityStatsWidget community={null} recentActivity={[]} streams={[]} />);
    // both Live Streams and Recent Activity are 0
    const zeros = screen.getAllByText('0');
    expect(zeros).toHaveLength(2);
  });

  it('counts recent activity from recentActivity array length', () => {
    render(<CommunityStatsWidget community={null} recentActivity={[{}, {}]} streams={[]} />);
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('shows 0 when streams is undefined', () => {
    render(<CommunityStatsWidget community={null} recentActivity={[]} streams={undefined} />);
    const zeros = screen.getAllByText('0');
    expect(zeros.length).toBeGreaterThanOrEqual(1);
  });

  it('shows 0 when recentActivity is undefined', () => {
    render(<CommunityStatsWidget community={null} recentActivity={undefined} streams={[]} />);
    const zeros = screen.getAllByText('0');
    expect(zeros.length).toBeGreaterThanOrEqual(1);
  });

  it('renders the card header text', () => {
    render(<CommunityStatsWidget community={null} recentActivity={[]} streams={[]} />);
    expect(screen.getByText('Community Stats')).toBeInTheDocument();
  });
});
