export type CategoryAccent = {
  bar: string;
  badge: string;
  dot: string;
};

export function categoryAccent(cat?: string | null): CategoryAccent {
  if (!cat) return { bar: 'bg-slate-300', badge: 'bg-slate-50 text-slate-500 border border-slate-200', dot: 'bg-slate-400' };
  const l = cat.toLowerCase();

  // Food & Dining
  if (/food|restaurant|caf[eé]|dining|eat|pub|bistro|bakery|cuisine|brunch|breakfast|lunch|dinner|snack|dessert|ice.?cream|pizza|sushi|ramen|noodle|street.?food|seafood|buffet/i.test(l))
    return { bar: 'bg-amber-400', badge: 'bg-amber-50 text-amber-700 border border-amber-200', dot: 'bg-amber-500' };

  // Culture & Arts
  if (/museum|art|cultur|history|gallery|theater|theatre|monument|exhibit|heritage|archeolog|archaeolog|palace|castle|ruin/i.test(l))
    return { bar: 'bg-violet-400', badge: 'bg-violet-50 text-violet-700 border border-violet-200', dot: 'bg-violet-500' };

  // Nature & Outdoors
  if (/nature|park|beach|outdoor|garden|hiking|trail|waterfall|lake|forest|mountain|island|canyon|reserve|wildlife|jungle|cliff|valley/i.test(l))
    return { bar: 'bg-emerald-400', badge: 'bg-emerald-50 text-emerald-700 border border-emerald-200', dot: 'bg-emerald-500' };

  // Shopping
  if (/shop|mall|market|boutique|store|souvenir|retail|bazaar|flea|duty.?free/i.test(l))
    return { bar: 'bg-rose-400', badge: 'bg-rose-50 text-rose-700 border border-rose-200', dot: 'bg-rose-500' };

  // Accommodation
  if (/hotel|hostel|resort|airbnb|stay|accommodation|lodg|inn|motel|villa|apartment|rental/i.test(l))
    return { bar: 'bg-blue-400', badge: 'bg-blue-50 text-blue-700 border border-blue-200', dot: 'bg-blue-500' };

  // Transport
  if (/airport|train|bus|transport|transit|ferry|port|station|subway|metro|taxi|transfer|flight|commute/i.test(l))
    return { bar: 'bg-slate-400', badge: 'bg-slate-100 text-slate-600 border border-slate-300', dot: 'bg-slate-500' };

  // Entertainment
  if (/entertainment|theme.?park|amusement|cinema|movie|concert|show|perform|festival|fair|carnival|circus|zoo|aquarium/i.test(l))
    return { bar: 'bg-fuchsia-400', badge: 'bg-fuchsia-50 text-fuchsia-700 border border-fuchsia-200', dot: 'bg-fuchsia-500' };

  // Sports & Adventure
  if (/sport|adventure|surf|dive|scuba|snorkel|ski|climb|kayak|cycle|bike|swim|water.?sport|skydiv|bungee|trek|rafting/i.test(l))
    return { bar: 'bg-teal-400', badge: 'bg-teal-50 text-teal-700 border border-teal-200', dot: 'bg-teal-500' };

  // Wellness & Spa
  if (/spa|wellness|massage|yoga|meditat|gym|fitness|sauna|thermal|hot.?spring|retreat/i.test(l))
    return { bar: 'bg-pink-400', badge: 'bg-pink-50 text-pink-700 border border-pink-200', dot: 'bg-pink-500' };

  // Religious & Spiritual
  if (/church|cathedral|temple|mosque|shrine|monastery|chapel|religious|spiritual|sacred|pagoda|stupa/i.test(l))
    return { bar: 'bg-stone-400', badge: 'bg-stone-100 text-stone-600 border border-stone-300', dot: 'bg-stone-500' };

  // Nightlife
  if (/nightlife|club|nightclub|lounge|rooftop|cocktail|bar.?crawl|party|disco/i.test(l))
    return { bar: 'bg-purple-500', badge: 'bg-purple-50 text-purple-700 border border-purple-200', dot: 'bg-purple-600' };

  // Landmarks & Viewpoints
  if (/landmark|viewpoint|view|lookout|panorama|observation|tower|bridge|square|plaza|sight/i.test(l))
    return { bar: 'bg-yellow-400', badge: 'bg-yellow-50 text-yellow-700 border border-yellow-200', dot: 'bg-yellow-500' };

  // Activities & Tours
  if (/activity|experience|tour|class|workshop|lesson|cooking|craft/i.test(l))
    return { bar: 'bg-orange-400', badge: 'bg-orange-50 text-orange-700 border border-orange-200', dot: 'bg-orange-500' };

  return { bar: 'bg-indigo-400', badge: 'bg-indigo-50 text-indigo-600 border border-indigo-200', dot: 'bg-indigo-500' };
}

/** Return a hex color for Google Maps PinElement based on event category. */
export function categoryPinColor(cat?: string | null): string {
  if (!cat) return '#4f46e5';
  const l = cat.toLowerCase();
  if (/food|restaurant|caf[eé]|dining|eat|pub|bistro|bakery|cuisine|brunch|breakfast|lunch|dinner|snack|dessert|ice.?cream|pizza|sushi|ramen|noodle|street.?food|seafood|buffet/i.test(l)) return '#f59e0b';
  if (/museum|art|cultur|history|gallery|theater|theatre|monument|exhibit|heritage|archeolog|archaeolog|palace|castle|ruin/i.test(l)) return '#8b5cf6';
  if (/nature|park|beach|outdoor|garden|hiking|trail|waterfall|lake|forest|mountain|island|canyon|reserve|wildlife|jungle|cliff|valley/i.test(l)) return '#10b981';
  if (/shop|mall|market|boutique|store|souvenir|retail|bazaar|flea|duty.?free/i.test(l)) return '#f43f5e';
  if (/hotel|hostel|resort|airbnb|stay|accommodation|lodg|inn|motel|villa|apartment|rental/i.test(l)) return '#3b82f6';
  if (/airport|train|bus|transport|transit|ferry|port|station|subway|metro|taxi|transfer|flight|commute/i.test(l)) return '#64748b';
  if (/entertainment|theme.?park|amusement|cinema|movie|concert|show|perform|festival|fair|carnival|circus|zoo|aquarium/i.test(l)) return '#d946ef';
  if (/sport|adventure|surf|dive|scuba|snorkel|ski|climb|kayak|cycle|bike|swim|water.?sport|skydiv|bungee|trek|rafting/i.test(l)) return '#14b8a6';
  if (/spa|wellness|massage|yoga|meditat|gym|fitness|sauna|thermal|hot.?spring|retreat/i.test(l)) return '#ec4899';
  if (/church|cathedral|temple|mosque|shrine|monastery|chapel|religious|spiritual|sacred|pagoda|stupa/i.test(l)) return '#78716c';
  if (/nightlife|club|nightclub|lounge|rooftop|cocktail|bar.?crawl|party|disco/i.test(l)) return '#7c3aed';
  if (/landmark|viewpoint|view|lookout|panorama|observation|tower|bridge|square|plaza|sight/i.test(l)) return '#eab308';
  if (/activity|experience|tour|class|workshop|lesson|cooking|craft/i.test(l)) return '#f97316';
  return '#4f46e5';
}
