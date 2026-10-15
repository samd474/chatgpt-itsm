import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Flag, Plus } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";
import { apiErrorMessage } from "../../api/client";
import { createResource, deleteResource, getResource, listAll, updateResource, ENDPOINTS } from "../../api/resources";
import { useAuth } from "../../auth/context";
import { hasRole } from "../../auth/roles";
import { Pill, PriorityBadge } from "../../components/badges";
import { RecordEditor } from "../../components/RecordEditor";
import { Avatar, Card, Drawer, ErrorState, LoadingState, Notice, PageHeader, Tabs } from "../../components/ui";
import type { Milestone, Project, ProjectTask } from "../../types";
import { formatDay } from "../../utils/format";
import { PROJECT_FIELDS, membersPayload, projectToRecord } from "./projectFields";

const COLUMNS: { value: ProjectTask["status"]; label: string }[] = [
  { value: "todo", label: "To do" }, { value: "in_progress", label: "In progress" }, { value: "blocked", label: "Blocked" }, { value: "done", label: "Done" },
];

function TaskEditor({ project, task, milestones, onClose }: { project: Project; task: ProjectTask | null; milestones: Milestone[]; onClose: () => void }) {
  const queryClient = useQueryClient();
  const people = [{ user: project.manager, name: project.manager_name }, ...project.members.map((m) => ({ user: m.user, name: m.name }))];
  return (
    <Drawer title={task ? task.number : "New task"} onClose={onClose}>
      <RecordEditor<ProjectTask>
        title="Task"
        record={task ? (task as unknown as Record<string, unknown>) : null}
        saveLabel={task ? "Save task" : "Create task"}
        fields={[
          { name: "title", label: "Title", required: true, span: true },
          { name: "status", label: "Status", type: "select", required: true, options: COLUMNS },
          { name: "priority", label: "Priority", type: "select", required: true, options: [1, 2, 3, 4].map((p) => ({ value: p, label: `P${p}` })) },
          { name: "assignee", label: "Assignee", type: "select", options: people.map((p) => ({ value: p.user, label: p.name })) },
          { name: "milestone", label: "Milestone", type: "select", options: milestones.map((m) => ({ value: m.id, label: m.name })) },
          { name: "due_date", label: "Due date", type: "date" },
          { name: "estimate_hours", label: "Estimate (hours)", type: "number" },
          { name: "description", label: "Description", type: "textarea" },
        ]}
        save={(payload) => task
          ? updateResource<ProjectTask>(ENDPOINTS.projectTasks, task.id, payload)
          : createResource<ProjectTask>(ENDPOINTS.projectTasks, { status: "todo", priority: 3, ...payload, project: project.id })}
        onSaved={async () => { await queryClient.invalidateQueries({ queryKey: ["project-tasks", project.id] }); await queryClient.invalidateQueries({ queryKey: ["project", String(project.id)] }); onClose(); }}
      />
    </Drawer>
  );
}

export function ProjectDetailPage() {
  const { id = "" } = useParams();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"board" | "milestones" | "settings">("board");
  const [editingTask, setEditingTask] = useState<ProjectTask | "new" | null>(null);
  const [milestoneName, setMilestoneName] = useState("");
  const [milestoneDue, setMilestoneDue] = useState("");
  const project = useQuery({ queryKey: ["project", id], queryFn: () => getResource<Project>(ENDPOINTS.projects, id) });
  const tasks = useQuery({ queryKey: ["project-tasks", Number(id)], queryFn: () => listAll<ProjectTask>(ENDPOINTS.projectTasks, { project: id, page_size: 200 }) });
  const milestones = useQuery({ queryKey: ["milestones", id], queryFn: () => listAll<Milestone>(ENDPOINTS.milestones, { project: id }) });
  const move = useMutation({
    mutationFn: ({ task, status }: { task: ProjectTask; status: ProjectTask["status"] }) => updateResource(ENDPOINTS.projectTasks, task.id, { status }),
    onSuccess: () => Promise.all([queryClient.invalidateQueries({ queryKey: ["project-tasks", Number(id)] }), queryClient.invalidateQueries({ queryKey: ["project", id] })]),
  });
  const addMilestone = useMutation({
    mutationFn: () => createResource(ENDPOINTS.milestones, { project: Number(id), name: milestoneName, due_date: milestoneDue || null }),
    onSuccess: () => { setMilestoneName(""); setMilestoneDue(""); void queryClient.invalidateQueries({ queryKey: ["milestones", id] }); },
  });
  const toggleMilestone = useMutation({
    mutationFn: (m: Milestone) => updateResource(ENDPOINTS.milestones, m.id, { completed: !m.completed }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["milestones", id] }),
  });
  const removeMilestone = useMutation({ mutationFn: (m: Milestone) => deleteResource(ENDPOINTS.milestones, m.id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["milestones", id] }) });

  if (project.isPending) return <LoadingState />;
  if (project.isError) return <ErrorState message={apiErrorMessage(project.error)} />;
  const p = project.data;
  const canManage = p.manager === user?.id || hasRole(user, "Administrator");
  const canContribute = canManage || p.members.some((m) => m.user === user?.id && m.role === "contributor");

  return (
    <>
      <PageHeader eyebrow={p.key} title={p.name} description={`${p.manager_name} · ${p.progress.done}/${p.progress.total} tasks done${p.target_date ? ` · target ${formatDay(p.target_date)}` : ""}`}
        actions={<><Pill value={p.status} />{canContribute && <button className="btn btn-primary" onClick={() => setEditingTask("new")}><Plus />New task</button>}</>} />
      <Tabs value={tab} onChange={setTab} tabs={[
        { value: "board", label: "Board", count: tasks.data?.length }, { value: "milestones", label: "Milestones", count: milestones.data?.length },
        { value: "settings", label: canManage ? "Settings" : "About" },
      ]} />
      {move.isError && <div style={{ marginBottom: 12 }}><Notice tone="error">{apiErrorMessage(move.error)}</Notice></div>}
      {tab === "board" && (
        <div className="board">
          {COLUMNS.map((col) => {
            const items = (tasks.data ?? []).filter((t) => t.status === col.value);
            return (
              <div className="column" key={col.value}>
                <div className="column-head"><span>{col.label}</span><span>{items.length}</span></div>
                {items.map((t) => (
                  <div className="kcard" key={t.id}>
                    <div className="row" style={{ cursor: "pointer" }} onClick={() => setEditingTask(t)}><span className="eyebrow">{t.number}</span><span className="spacer" /><PriorityBadge priority={t.priority} /></div>
                    <strong style={{ fontWeight: 500, cursor: "pointer" }} onClick={() => setEditingTask(t)}>{t.title}</strong>
                    <div className="row">
                      {t.assignee_name ? <><Avatar name={t.assignee_name} />{t.assignee_name}</> : "Unassigned"}
                      <span className="spacer" />
                      {t.due_date && formatDay(t.due_date)}
                    </div>
                    {(canContribute || t.assignee === user?.id) && (
                      <select className="select" style={{ height: 28, fontSize: 12 }} value={t.status} aria-label="Move task"
                        onChange={(e) => move.mutate({ task: t, status: e.target.value as ProjectTask["status"] })}>
                        {COLUMNS.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                      </select>
                    )}
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      )}
      {tab === "milestones" && (
        <Card title="Milestones">
          {milestones.data?.length === 0 && <p className="subtle">No milestones yet.</p>}
          <div className="list">
            {milestones.data?.map((m) => (
              <div className="list-item" key={m.id}>
                <Flag color={m.completed ? "var(--green)" : undefined} />
                <span style={{ textDecoration: m.completed ? "line-through" : undefined }}>{m.name}</span>
                <span className="spacer" /><span className="subtle">{formatDay(m.due_date)}</span>
                {canManage && <>
                  <button className="btn btn-ghost btn-sm" onClick={() => toggleMilestone.mutate(m)}>{m.completed ? "Reopen" : "Complete"}</button>
                  <button className="btn btn-ghost btn-sm" onClick={() => removeMilestone.mutate(m)}>Remove</button>
                </>}
              </div>
            ))}
          </div>
          {canManage && (
            <form className="row" style={{ marginTop: 12 }} onSubmit={(e) => { e.preventDefault(); addMilestone.mutate(); }}>
              <input className="input" style={{ flex: 1 }} placeholder="Milestone name" value={milestoneName} onChange={(e) => setMilestoneName(e.target.value)} />
              <input className="input" style={{ width: 170 }} type="date" value={milestoneDue} onChange={(e) => setMilestoneDue(e.target.value)} />
              <button className="btn btn-secondary" disabled={!milestoneName.trim()}>Add</button>
            </form>
          )}
        </Card>
      )}
      {tab === "settings" && (
        <RecordEditor<Project> key={p.id + String(p.progress.total)} title="Project" fields={PROJECT_FIELDS} record={projectToRecord(p)} readOnly={!canManage}
          save={(payload) => updateResource<Project>(ENDPOINTS.projects, p.id, membersPayload(payload))}
          onSaved={(saved) => queryClient.setQueryData(["project", id], saved)} />
      )}
      {editingTask && <TaskEditor project={p} task={editingTask === "new" ? null : editingTask} milestones={milestones.data ?? []} onClose={() => setEditingTask(null)} />}
    </>
  );
}
