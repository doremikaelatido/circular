import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, Bell, ContactRound, LogOut, Plus, Search, Settings, UserRound } from "lucide-react";
import { Link, Navigate, Route, Routes, useLocation, useSearchParams } from "react-router-dom";
import { EventFormDialog } from "./components/EventFormDialog";
import { Button } from "./components/ui/Button";
import { useAuth } from "./features/auth/AuthContext";
import { Calendar } from "./features/calendar/Calendar";
import { api } from "./lib/api";
import { AuthPage } from "./pages/AuthPage";
import { ConnectionsPage } from "./pages/ConnectionsPage";
import { InboxPage } from "./pages/InboxPage";
import type { CalendarViewMode, Connection, EventItem } from "./types";

function startOfWeek(date: Date) {
  const start = new Date(date);
  start.setHours(0, 0, 0, 0);
  start.setDate(start.getDate() - start.getDay());
  return start;
}

function toISOString(date: Date) {
  return date.toISOString();
}

function HomePage() {
  const { user, logout } = useAuth();
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date()));
  const [view, setView] = useState<CalendarViewMode>("mine");
  const [createOpen, setCreateOpen] = useState(false);
  const [editEvent, setEditEvent] = useState<EventItem | null>(null);
  const [selected, setSelected] = useState<EventItem | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const client = useQueryClient();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const start = useMemo(() => new Date(weekStart), [weekStart]);
  const end = useMemo(() => {
    const date = new Date(weekStart);
    date.setDate(date.getDate() + 7);
    return date;
  }, [weekStart]);
  const calendar = useQuery({
    queryKey: ["calendar", view, start.toISOString(), end.toISOString()],
    queryFn: () => api<EventItem[]>(`/calendar?view=${view}&starts_at=${encodeURIComponent(toISOString(start))}&ends_at=${encodeURIComponent(toISOString(end))}`),
  });
  const invitations = useQuery({
    queryKey: ["invitations"],
    queryFn: () => api<EventItem[]>("/events/invitations"),
  });
  const connections = useQuery({ queryKey: ["connections"], queryFn: () => api<Connection[]>("/users/connections") });
  const unread = useQuery({ queryKey: ["unread-count"], queryFn: () => api<{ count: number }>("/notifications/unread-count") });

  useEffect(() => {
    const eventId = Number(searchParams.get("event"));
    if (!eventId) return;
    api<EventItem>(`/events/${eventId}`).then((event) => {
      setSelected(event);
      setSearchParams((params) => { params.delete("event"); return params; }, { replace: true });
    }).catch((error: unknown) => setActionError(error instanceof Error ? error.message : "Event is no longer available."));
  }, [searchParams, setSearchParams]);

  const mutation = useMutation({
    mutationFn: ({ path, method = "POST" }: { path: string; method?: string }) => api(path, { method }),
    onSuccess: async () => {
      setActionError(null);
      await client.invalidateQueries({ queryKey: ["calendar"] });
      await client.invalidateQueries({ queryKey: ["invitations"] });
      await client.invalidateQueries({ queryKey: ["notifications"] });
      await client.invalidateQueries({ queryKey: ["unread-count"] });
      setSelected(null);
    },
    onError: (error) => setActionError(error instanceof Error ? error.message : "That action could not be completed."),
  });

  const selectedIsInList = calendar.data?.find((event) => event.id === selected?.id);
  const eventForDialog = selectedIsInList ?? selected;
  const rangeLabel = `${start.toLocaleDateString()} – ${end.toLocaleDateString()}`;

  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  return (
    <div className="app-shell">
      <header className="app-header">
        <Link className="brand" to="/"><span className="brand-mark-small"><CalendarDays size={20} /></span><strong>Circle</strong></Link>
        <div className="header-center">
          <label className="search-box"><Search size={17} /><input aria-label="Search events" placeholder="Search events" disabled /></label>
          <Button className="button button-primary" onClick={() => { setEditEvent(null); setCreateOpen(true); }}><Plus size={17} />Create Event</Button>
        </div>
        <nav className="header-actions" aria-label="Main navigation">
          <Link className="icon-button" to="/connections" aria-label="Connections" title="Connections"><ContactRound /></Link>
          <Link className="icon-button notification-link" to="/inbox" aria-label={`Inbox${unread.data?.count ? `, ${unread.data.count} unread` : ""}`} title="Inbox"><Bell />{Boolean(unread.data?.count) && <span className="badge">{unread.data?.count}</span>}</Link>
          <Link className="icon-button" to="/profile" aria-label="Profile" title="Profile"><UserRound /></Link>
          <Link className="icon-button" to="/settings" aria-label="Settings" title="Settings"><Settings /></Link>
          <button className="icon-button" aria-label="Log out" title="Log out" onClick={() => void logout()}><LogOut /></button>
        </nav>
      </header>
      <Routes>
        <Route path="/" element={
          <main className="dashboard">
            <div className="welcome-row"><div><h1>Good to see you, {user.nickname}</h1><p>Make time for the people who matter.</p></div><span className="date-caption">{rangeLabel}</span></div>
            <div className="calendar-view-tabs" role="tablist" aria-label="Calendar view">
              <button role="tab" aria-selected={view === "mine"} className={view === "mine" ? "selected" : ""} onClick={() => setView("mine")}>My Calendar</button>
              <button role="tab" aria-selected={view === "circle"} className={view === "circle" ? "selected" : ""} onClick={() => setView("circle")}>My Circle’s Calendar</button>
            </div>
            <Calendar
              events={calendar.data ?? []}
              view={view}
              currentUserId={user.id}
              weekStart={weekStart}
              loading={calendar.isLoading}
              error={calendar.error instanceof Error ? calendar.error.message : null}
              onPreviousWeek={() => setWeekStart((date) => { const next = new Date(date); next.setDate(next.getDate() - 7); return next; })}
              onNextWeek={() => setWeekStart((date) => { const next = new Date(date); next.setDate(next.getDate() + 7); return next; })}
              onToday={() => setWeekStart(startOfWeek(new Date()))}
              onSelectEvent={setSelected}
            />
            {unread.error && <div className="error-banner" role="alert">{unread.error.message}</div>}
            {invitations.error && <div className="error-banner" role="alert">{invitations.error.message}</div>}
            {invitations.data && invitations.data.length > 0 && (
              <section className="surface-card invitation-list">
                <h2>Event invitations</h2>
                {invitations.data.map((event) => <button className="invitation-item" key={event.id} onClick={() => setSelected(event)}>
                  <span><strong>{event.title}</strong><small>{new Date(event.starts_at).toLocaleString()} · {event.location}</small></span>
                  <span className="invitation-action">{event.current_user_participating ? "View event" : "Review invitation"}</span>
                </button>)}
              </section>
            )}
          </main>
        } />
        <Route path="/connections" element={<ConnectionsPage />} />
        <Route path="/inbox" element={<InboxPage />} />
        <Route path="/profile" element={<main className="page-content"><h1>Profile</h1><section className="surface-card"><UserRound /><h2>{user.nickname}</h2><p>{user.email}</p><p className="page-subtitle">Profile settings are limited in this first version.</p></section></main>} />
        <Route path="/settings" element={<main className="page-content"><h1>Settings</h1><section className="surface-card"><Settings /><h2>Account</h2><p className="page-subtitle">Account settings are limited in this first version.</p><button className="button button-outline" onClick={() => void logout()}>Log out</button></section></main>} />
      </Routes>
      {location.pathname === "/" && eventForDialog && (
        <div className="detail-backdrop" role="presentation" onClick={() => { setSelected(null); setActionError(null); }}>
          <section className="event-detail" role="dialog" aria-modal="true" aria-label={eventForDialog.title} onClick={(event) => event.stopPropagation()}>
            <button className="detail-close" aria-label="Close event details" onClick={() => setSelected(null)}>×</button>
            <span className={`category-pill category-${eventForDialog.category}`}>{eventForDialog.category}</span>
            <h2>{eventForDialog.title}</h2>
            <p>{new Date(eventForDialog.starts_at).toLocaleString()} – {new Date(eventForDialog.ends_at).toLocaleTimeString()}</p>
            <p>{eventForDialog.location}</p>
            {eventForDialog.description && <p>{eventForDialog.description}</p>}
            <p>{eventForDialog.participant_count} participating</p>
            {actionError && <div className="error-banner">{actionError}</div>}
            <div className="inline-actions">
              {eventForDialog.current_user_is_creator && <>
                <button className="button button-outline" onClick={() => { setEditEvent(eventForDialog); setCreateOpen(true); setSelected(null); }}>Edit</button>
                <button className="button button-outline" onClick={() => mutation.mutate({ path: `/events/${eventForDialog.id}/cancel` })}>Cancel event</button>
              </>}
              {eventForDialog.current_user_participating
                ? <button className="button button-outline" onClick={() => mutation.mutate({ path: `/events/${eventForDialog.id}/leave` })}>Leave event</button>
                : <button className="button button-primary" onClick={() => mutation.mutate({ path: `/events/${eventForDialog.id}/join` })}>Join</button>}
            </div>
          </section>
        </div>
      )}
      <EventFormDialog
        open={createOpen}
        event={editEvent}
        connections={connections.data ?? []}
        onOpenChange={(open) => { setCreateOpen(open); if (!open) setEditEvent(null); }}
        onSaved={() => { void client.invalidateQueries({ queryKey: ["calendar"] }); }}
      />
    </div>
  );
}

export function App() {
  const { user } = useAuth();
  return <Routes>
    <Route path="/login" element={user ? <Navigate to="/" replace /> : <AuthPage />} />
    <Route path="/*" element={user ? <HomePage /> : <Navigate to="/login" replace />} />
  </Routes>;
}
