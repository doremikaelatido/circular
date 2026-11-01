import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { InboxNotification } from "../types";

export function InboxPage() {
  const client = useQueryClient();
  const notifications = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api<InboxNotification[]>("/notifications"),
  });

  async function markRead(id: number) {
    await api(`/notifications/${id}/read`, { method: "POST" });
    await Promise.all([
      client.invalidateQueries({ queryKey: ["notifications"] }),
      client.invalidateQueries({ queryKey: ["unread-count"] }),
    ]);
  }

  return <main className="page-content">
    <h1>Inbox</h1><p className="page-subtitle">Updates from your circle.</p>
    <section className="surface-card">
      {notifications.isLoading && <p>Loading notifications…</p>}
      {notifications.error && <p className="error-banner">{notifications.error.message}</p>}
      {notifications.data?.length === 0 && <p className="empty-state">You’re all caught up.</p>}
      {notifications.data?.map((notification) => <article className={`notification-row ${notification.read ? "" : "unread"}`} key={notification.id}>
        <div><p>{notification.message}</p><time>{new Date(notification.created_at).toLocaleString()}</time></div>
        <div className="inline-actions">
          {notification.event_id && <Link className="button button-outline" to={`/?event=${notification.event_id}`}>View event</Link>}
          {!notification.read && <button className="button button-primary" onClick={() => void markRead(notification.id)}>Mark read</button>}
        </div>
      </article>)}
    </section>
  </main>;
}
