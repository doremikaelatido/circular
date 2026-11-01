import * as Dialog from "@radix-ui/react-dialog";
import { zodResolver } from "@hookform/resolvers/zod";
import { X } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api, jsonBody } from "../lib/api";
import type { Connection, EventItem } from "../types";
import { Button } from "./ui/Button";
import { Input } from "./ui/Input";

const schema = z.object({
  title: z.string().trim().min(1, "Add a title").max(120),
  category: z.enum(["sports", "food", "art", "social"]),
  description: z.string().max(2000),
  starts_on: z.string().min(1, "Choose a start date"),
  starts_time: z.string().min(1, "Choose a start time"),
  ends_on: z.string().min(1, "Choose an end date"),
  ends_time: z.string().min(1, "Choose an end time"),
  location: z.string().trim().min(1, "Add a location").max(200),
  invite_user_ids: z.array(z.number()),
}).refine((value) => {
  const start = new Date(`${value.starts_on}T${value.starts_time}`);
  const end = new Date(`${value.ends_on}T${value.ends_time}`);
  return !Number.isNaN(start.getTime()) && !Number.isNaN(end.getTime()) && end > start;
}, {
  message: "End date and time must be later than start date and time",
  path: ["ends_time"],
});

type FormValues = z.infer<typeof schema>;

const emptyFormValues: FormValues = {
  title: "",
  category: "social",
  description: "",
  starts_on: "",
  starts_time: "",
  ends_on: "",
  ends_time: "",
  location: "",
  invite_user_ids: [],
};

function toLocalDate(value: string) {
  const date = new Date(value);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function toLocalTime(value: string) {
  const date = new Date(value);
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${hours}:${minutes}`;
}

interface Props {
  open: boolean;
  event?: EventItem | null;
  connections: Connection[];
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}

export function EventFormDialog({ open, event, connections, onOpenChange, onSaved }: Props) {
  const { register, handleSubmit, reset, setError, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: emptyFormValues,
  });

  useEffect(() => {
    if (!open) {
      reset(emptyFormValues);
      return;
    }
    if (event) {
      reset({
        title: event.title,
        category: event.category,
        description: event.description,
        starts_on: toLocalDate(event.starts_at),
        starts_time: toLocalTime(event.starts_at),
        ends_on: toLocalDate(event.ends_at),
        ends_time: toLocalTime(event.ends_at),
        location: event.location,
        invite_user_ids: [],
      });
    } else {
      reset(emptyFormValues);
    }
  }, [open, event, reset]);

  async function submit(values: FormValues) {
    try {
      const payload = {
        title: values.title,
        category: values.category,
        description: values.description,
        location: values.location,
        invite_user_ids: values.invite_user_ids,
        starts_at: new Date(`${values.starts_on}T${values.starts_time}`).toISOString(),
        ends_at: new Date(`${values.ends_on}T${values.ends_time}`).toISOString(),
      };
      await api(event ? `/events/${event.id}` : "/events", {
        method: event ? "PATCH" : "POST",
        body: jsonBody(payload),
      });
      onSaved();
      reset();
      onOpenChange(false);
    } catch (error) {
      setError("root", { message: error instanceof Error ? error.message : "Could not save event" });
    }
  }

  const acceptedConnections = connections.filter((connection) => connection.status === "accepted");
  return (
    <Dialog.Root open={open} onOpenChange={(next) => {
      if (!next) reset(emptyFormValues);
      onOpenChange(next);
    }}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content">
          <div className="dialog-heading">
            <div><Dialog.Title>{event ? "Edit event" : "Create an event"}</Dialog.Title><Dialog.Description>Bring your circle together for something fun.</Dialog.Description></div>
            <Dialog.Close asChild><button className="icon-button" aria-label="Close"><X size={18} /></button></Dialog.Close>
          </div>
          <form className="form-stack" onSubmit={handleSubmit(submit)}>
            <label>Title<Input autoFocus {...register("title")} placeholder="e.g. Sunday tennis" /></label>
            {errors.title && <small className="field-error">{errors.title.message}</small>}
            <label>Category<select {...register("category")}><option value="sports">Sports</option><option value="food">Food</option><option value="art">Art</option><option value="social">Social</option></select></label>
            <div className="schedule-fields">
              <div className="schedule-group">
                <h3>Starts</h3>
                <div className="schedule-inputs">
                  <label>Date<Input type="date" {...register("starts_on")} /></label>
                  <label>Time<Input type="time" {...register("starts_time")} /></label>
                </div>
                {errors.starts_on && <small className="field-error">{errors.starts_on.message}</small>}
                {errors.starts_time && <small className="field-error">{errors.starts_time.message}</small>}
              </div>
              <div className="schedule-group">
                <h3>Ends</h3>
                <div className="schedule-inputs">
                  <label>Date<Input type="date" {...register("ends_on")} /></label>
                  <label>Time<Input type="time" {...register("ends_time")} /></label>
                </div>
                {errors.ends_on && <small className="field-error">{errors.ends_on.message}</small>}
                {errors.ends_time && <small className="field-error">{errors.ends_time.message}</small>}
              </div>
            </div>
            <label>Location<Input {...register("location")} placeholder="Neighborhood or venue" /></label>
            {errors.location && <small className="field-error">{errors.location.message}</small>}
            <label>Description<textarea rows={3} {...register("description")} placeholder="Add a few details…" /></label>
            {!event && acceptedConnections.length > 0 && (
              <label>Pre-invite connections <select multiple size={Math.min(acceptedConnections.length, 4)} {...register("invite_user_ids", { setValueAs: (values: string[]) => values.map(Number) })}>
                {acceptedConnections.map((connection) => <option key={connection.id} value={connection.user_id}>{connection.nickname}</option>)}
              </select><small>Invites do not confirm participation.</small></label>
            )}
            {errors.root && <div className="error-banner" role="alert">{errors.root.message}</div>}
            <div className="form-actions"><Dialog.Close asChild><Button type="button" variant="outline" className="button button-outline">Cancel</Button></Dialog.Close><Button className="button button-primary" disabled={isSubmitting}>{isSubmitting ? "Saving…" : event ? "Save changes" : "Create event"}</Button></div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
