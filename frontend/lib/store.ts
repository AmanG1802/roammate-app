import { create } from 'zustand';

interface Event {
  id: string;
  trip_id: string;
  title: string;
  start_time: Date;
  end_time: Date;
  lat: number;
  lng: number;
}

interface Idea {
  id: string;
  title: string;
  lat: number;
  lng: number;
}

interface TripState {
  activeTripId: string | null;
  ideas: Idea[];
  events: Event[];
  collaborators: { id: string; name: string; color: string; activeEventId?: string }[];
  
  setActiveTrip: (id: string) => void;
  setIdeas: (ideas: Idea[]) => void;
  setEvents: (events: Event[]) => void;
  addIdea: (idea: Idea) => void;
  addEvent: (event: Event) => void;
  moveIdeaToTimeline: (ideaId: string, startTime: Date) => void;
  updateCollaboratorStatus: (userId: string, activeEventId?: string) => void;
}

export const useTripStore = create<TripState>((set) => ({
  activeTripId: '1',
  ideas: [],
  events: [],
  collaborators: [
    { id: '1', name: 'You', color: '#4f46e5' },
    { id: '2', name: 'Sarah', color: '#ec4899' },
  ],
  
  setActiveTrip: (id) => set({ activeTripId: id }),
  setIdeas: (ideas) => set({ ideas }),
  setEvents: (events) => set({ events }),
  addIdea: (idea) => set((state) => ({ ideas: [idea, ...state.ideas] })),
  addEvent: (event) => set((state) => ({ events: [...state.events, event] })),
  
  moveIdeaToTimeline: (ideaId, startTime) => set((state) => {
    const idea = state.ideas.find(i => i.id === ideaId);
    if (!idea) return state;
    
    const newEvent: Event = {
      id: Math.random().toString(36).substr(2, 9),
      trip_id: state.activeTripId || '1',
      title: idea.title,
      start_time: startTime,
      end_time: new Date(startTime.getTime() + 60 * 60 * 1000),
      lat: idea.lat,
      lng: idea.lng,
    };

    return {
      ideas: state.ideas.filter(i => i.id !== ideaId),
      events: [...state.events, newEvent].sort((a, b) => a.start_time.getTime() - b.start_time.getTime()),
    };
  }),

  updateCollaboratorStatus: (userId, activeEventId) => set((state) => ({
    collaborators: state.collaborators.map(c => 
      c.id === userId ? { ...c, activeEventId } : c
    )
  })),
}));
