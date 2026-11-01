import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, jsonBody } from "../lib/api";
import type { Connection } from "../types";

export function ConnectionsPage() {
  const [search, setSearch] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const client = useQueryClient();
  const connections = useQuery({ queryKey: ["connections"], queryFn: () => api<Connection[]>("/users/connections") });
  const results = useQuery({
    queryKey: ["user-search", search],
    queryFn: () => api<Array<{ id: number; nickname: string }>>(`/users/search?q=${encodeURIComponent(search)}`),
    enabled: search.trim().length >= 2,
  });
  const mutation = useMutation({
    mutationFn: ({ path, method = "POST", body }: { path: string; method?: string; body?: unknown }) =>
      api(path, { method, ...(body === undefined ? {} : { body: jsonBody(body) }) }),
    onSuccess: async () => {
      setMessage("Connection updated.");
      await Promise.all([
        client.invalidateQueries({ queryKey: ["connections"] }),
        client.invalidateQueries({ queryKey: ["calendar"] }),
      ]);
    },
    onError: (error) => setMessage(error instanceof Error ? error.message : "Could not update connection."),
  });

  return <main className="page-content">
    <h1>Connections</h1><p className="page-subtitle">Connect with people you know. Only accepted connections are included in your circle calendar.</p>
    <section className="surface-card">
      <label>Find people<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by nickname or exact email" /></label>
      {results.error && <p className="error-banner" role="alert">{results.error.message}</p>}
      {results.data?.map((person) => <div className="list-row" key={person.id}><span>{person.nickname}</span><button className="button button-outline" onClick={() => mutation.mutate({ path: "/users/connections", method: "POST", body: { user_id: person.id } })} aria-label={`Connect with ${person.nickname}`}>Connect</button></div>)}
    </section>
    <section className="surface-card"><h2>Your requests and connections</h2>
      {connections.error && <p className="error-banner" role="alert">{connections.error.message}</p>}
      {connections.data?.map((connection) => <div className="list-row" key={connection.id}>
        <span>{connection.nickname}{connection.status === "accepted" ? " · Connected" : ` · ${connection.direction} request`}</span>
        <div className="inline-actions">
          {connection.status === "pending" && connection.direction === "incoming" && <><button className="button button-primary" onClick={() => mutation.mutate({ path: `/users/connections/${connection.id}/accept` })}>Accept</button><button className="button button-outline" onClick={() => mutation.mutate({ path: `/users/connections/${connection.id}/decline` })}>Decline</button></>}
          {connection.status === "accepted" && <button className="button button-outline" onClick={() => mutation.mutate({ path: `/users/connections/${connection.id}`, method: "DELETE" })}>Remove</button>}
        </div>
      </div>)}
    </section>
    {message && <p role="status" className="page-subtitle">{message}</p>}
  </main>;
}
