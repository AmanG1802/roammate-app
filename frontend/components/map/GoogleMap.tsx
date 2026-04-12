'use client';

import { useEffect, useRef, useState } from 'react';
import { Loader } from '@googlemaps/js-api-loader';
import { useTripStore } from '@/lib/store';

export default function GoogleMap() {
  const mapRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<google.maps.Map | null>(null);
  const { events, ideas } = useTripStore();
  const markersRef = useRef<google.maps.Marker[]>([]);

  useEffect(() => {
    const loader = new Loader({
      apiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '',
      version: 'weekly',
      libraries: ['places']
    });

    loader.load().then(() => {
      if (mapRef.current && !map) {
        const newMap = new google.maps.Map(mapRef.current, {
          center: { lat: 41.8902, lng: 12.4922 }, // Default to Rome
          zoom: 13,
          mapId: 'ROAMMATE_MAP_ID', // For advanced styling if needed
          disableDefaultUI: true,
          zoomControl: true,
        });
        setMap(newMap);
      }
    });
  }, [map]);

  // Update markers when events or ideas change
  useEffect(() => {
    if (!map) return;

    // Clear existing markers
    markersRef.current.forEach(marker => marker.setMap(null));
    markersRef.current = [];

    const bounds = new google.maps.LatLngBounds();
    let hasMarkers = false;

    // Add markers for events (Itinerary)
    events.forEach((event, index) => {
      const marker = new google.maps.Marker({
        position: { lat: event.lat, lng: event.lng },
        map: map,
        title: event.title,
        label: {
          text: (index + 1).toString(),
          color: 'white',
          fontWeight: 'bold'
        },
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          fillColor: '#4f46e5', // Indigo-600
          fillOpacity: 1,
          strokeWeight: 2,
          strokeColor: '#ffffff',
          scale: 12,
        }
      });
      markersRef.current.push(marker);
      bounds.extend(marker.getPosition()!);
      hasMarkers = true;
    });

    // Add markers for ideas (Idea Bin)
    ideas.forEach((idea) => {
      const marker = new google.maps.Marker({
        position: { lat: idea.lat, lng: idea.lng },
        map: map,
        title: idea.title,
        icon: {
          path: google.maps.SymbolPath.BACKWARD_CLOSED_ARROW,
          fillColor: '#94a3b8', // Slate-400
          fillOpacity: 0.6,
          strokeWeight: 1,
          strokeColor: '#ffffff',
          scale: 4,
        }
      });
      markersRef.current.push(marker);
      bounds.extend(marker.getPosition()!);
      hasMarkers = true;
    });

    if (hasMarkers && (events.length > 0 || ideas.length > 0)) {
        // Only fit bounds if we have markers and it's not the initial state
        map.fitBounds(bounds);
        // Don't zoom in too much for a single marker
        if (map.getZoom()! > 15) map.setZoom(15);
    }
  }, [map, events, ideas]);

  return (
    <div className="flex-1 h-full relative">
      <div ref={mapRef} className="absolute inset-0" />
      
      {/* Overlay controls could go here */}
      <div className="absolute top-4 left-4 z-10 bg-white/90 backdrop-blur p-2 rounded-lg shadow-md border border-slate-200">
        <span className="text-xs font-bold text-slate-600 uppercase tracking-wider px-2">Live Route View</span>
      </div>
    </div>
  );
}
