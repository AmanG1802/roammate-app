import { describe, it, expect, beforeEach } from 'vitest';
import { useTripStore } from '../lib/store';

describe('useTripStore', () => {
  beforeEach(() => {
    // Reset state before each test
    useTripStore.setState({
      activeTripId: '1',
      ideas: [],
      events: [],
      collaborators: [
        { id: '1', name: 'You', color: '#4f46e5' },
        { id: '2', name: 'Sarah', color: '#ec4899' },
      ],
    });
  });

  it('should add an idea', () => {
    const { addIdea } = useTripStore.getState();
    const mockIdea = { id: 'test-1', title: 'Test Idea', lat: 1, lng: 1 };
    
    addIdea(mockIdea);
    
    expect(useTripStore.getState().ideas).toHaveLength(1);
    expect(useTripStore.getState().ideas[0].title).toBe('Test Idea');
  });

  it('should move an idea to the timeline', () => {
    const { addIdea, moveIdeaToTimeline } = useTripStore.getState();
    const mockIdea = { id: 'test-1', title: 'Test Idea', lat: 1, lng: 1 };
    
    addIdea(mockIdea);
    const startTime = new Date(2026, 4, 12, 10, 0);
    moveIdeaToTimeline('test-1', startTime);
    
    const state = useTripStore.getState();
    expect(state.ideas).toHaveLength(0);
    expect(state.events).toHaveLength(1);
    expect(state.events[0].title).toBe('Test Idea');
    expect(state.events[0].start_time).toEqual(startTime);
  });

  it('should update collaborator status', () => {
    const { updateCollaboratorStatus } = useTripStore.getState();
    
    updateCollaboratorStatus('2', 'event-1');
    
    const sarah = useTripStore.getState().collaborators.find(c => c.id === '2');
    expect(sarah?.activeEventId).toBe('event-1');
  });
});
