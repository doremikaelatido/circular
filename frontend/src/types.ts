export type Category = "sports" | "food" | "art" | "social";
export type CalendarViewMode = "mine" | "circle";

export interface User {
  id: number;
  email: string;
  nickname: string;
  gender: string | null;
}

export interface EventItem {
  id: number;
  creator_id: number;
  title: string;
  description: string;
  category: Category;
  starts_at: string;
  ends_at: string;
  location: string;
  status: "active" | "cancelled";
  participant_count: number;
  current_user_participating: boolean;
  current_user_is_creator: boolean;
}

export interface Connection {
  id: number;
  user_id: number;
  nickname: string;
  status: "pending" | "accepted" | "declined";
  direction: "incoming" | "outgoing";
}

export interface InboxNotification {
  id: number;
  actor_nickname: string;
  event_id: number | null;
  event_title: string | null;
  read: boolean;
  created_at: string;
  message: string;
}
