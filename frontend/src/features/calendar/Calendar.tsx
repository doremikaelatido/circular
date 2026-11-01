import { useEffect, useRef } from "react";
import FullCalendar from "@fullcalendar/react";
import timeGridPlugin from "@fullcalendar/timegrid";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { EventClickArg, EventContentArg } from "@fullcalendar/core";
import type { CalendarViewMode, EventItem } from "../../types";

export interface CalendarProps {
  events: EventItem[];
  view: CalendarViewMode;
  currentUserId: number;
  weekStart: Date;
  loading: boolean;
  error: string | null;
  onPreviousWeek: () => void;
  onNextWeek: () => void;
  onToday: () => void;
  onSelectEvent: (event: EventItem) => void;
}

function renderEventContent({ timeText, event }: EventContentArg, view: CalendarViewMode) {
  const calendarEvent = event.extendedProps.event as EventItem;
  return (
    <div className="calendar-event-content">
      <strong>{event.title}</strong>
      <span>{timeText}</span>
      <span>{calendarEvent.location}</span>
      {view === "circle" && calendarEvent.current_user_participating && (
        <span className="joining-event-chip">JOINING</span>
      )}
    </div>
  );
}

export function Calendar({ events, view, currentUserId, weekStart, loading, error, onPreviousWeek, onNextWeek, onToday, onSelectEvent }: CalendarProps) {
  const calendarRef = useRef<FullCalendar | null>(null);
  const weekEnd = new Date(weekStart);
  weekEnd.setDate(weekEnd.getDate() + 6);
  const visibleEvents = events.filter((event) => view !== "circle" || event.creator_id !== currentUserId);

  useEffect(() => {
    calendarRef.current?.getApi().gotoDate(weekStart);
  }, [weekStart]);

  function selectEvent(info: EventClickArg) {
    const event = info.event.extendedProps.event as EventItem;
    onSelectEvent(event);
  }

  return (
    <section className="calendar-panel" aria-label="Weekly calendar">
      <div className="calendar-toolbar">
        <div>
          <h2>{new Intl.DateTimeFormat(undefined, { month: "long", year: "numeric" }).format(weekStart)}</h2>
          <p>
            {new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(weekStart)}
            {" – "}
            {new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(weekEnd)}
          </p>
        </div>
        <div className="calendar-nav">
          <button className="button button-outline" onClick={onToday}>Today</button>
          <button className="icon-button" aria-label="Previous week" onClick={onPreviousWeek}><ChevronLeft /></button>
          <button className="icon-button" aria-label="Next week" onClick={onNextWeek}><ChevronRight /></button>
        </div>
      </div>
      {error && <div className="error-banner" role="alert">{error}</div>}
      <div className="fullcalendar-container" aria-busy={loading}>
        <FullCalendar
          ref={calendarRef}
          plugins={[timeGridPlugin]}
          initialView="timeGridWeek"
          initialDate={weekStart}
          firstDay={0}
          headerToolbar={false}
          allDaySlot={false}
          slotMinTime="06:00:00"
          slotMaxTime="23:00:00"
          slotLabelInterval="01:00"
          nowIndicator
          height="auto"
          events={visibleEvents.map((event) => ({
            id: String(event.id),
            title: event.title,
            start: event.starts_at,
            end: event.ends_at,
            classNames: [
              `category-${event.category}`,
              ...(event.current_user_participating ? ["joined-event"] : []),
            ],
            extendedProps: { event },
          }))}
          eventContent={(info) => renderEventContent(info, view)}
          eventClick={selectEvent}
        />
      </div>
      {loading && <div className="loading-overlay">Loading calendar…</div>}
      {!loading && visibleEvents.length === 0 && <p className="empty-state">No upcoming events this week. Create an event or check your circle.</p>}
    </section>
  );
}
