import { useQuery } from "@tanstack/react-query";
import { FolderKanban, Plus } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createResource, listAll, ENDPOINTS } from "../../api/resources";
import { useAuth } from "../../auth/context";
import { hasRole } from "../../auth/roles";
import { Pill } from "../../components/badges";
import { RecordEditor } from "../../components/RecordEditor";
import { Drawer, EmptyState, LoadingState, PageHeader, Tabs } from "../../components/ui";
import type { Project } from "../../types";
import { formatDay } from "../../utils/format";
import { PROJECT_FIELDS, membersPayload } from "./projectFields";

export function ProjectsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [status, setStatus] = useState("active");
  const [creating, setCreating] = useState(false);
  const query = useQuery({ queryKey: ["projects", status], queryFn: () => listAll<Project>(ENDPOINTS.projects, { status: status || undefined, page_size: 200 }) });

  return (
    <>
      <PageHeader title="Projects" description="Planned work with tasks, milestones and owners."
        actions={hasRole(user, "Manager", "Administrator") && <button className="btn btn-primary" onClick={() => setCreating(true)}><Plus />New project</button>} />
      <Tabs value={status} onChange={setStatus} tabs={[
        { value: "active", label: "Active" }, { value: "proposed", label: "Proposed" }, { value: "on_hold", label: "On hold" },
        { value: "completed", label: "Completed" }, { value: "", label: "All" },
      ]} />
      {query.isPending && <LoadingState />}
      {query.data?.length === 0 && <EmptyState title="No projects here" message="Projects you manage or belong to show up here." />}
      <div className="tiles">
        {query.data?.map((p) => (
          <Link key={p.id} className="tile" to={`/projects/${p.id}`}>
            <div className="row"><span className="tile-icon"><FolderKanban /></span><span className="eyebrow">{p.key}</span><span className="spacer" /><Pill value={p.status} /></div>
            <h3>{p.name}</h3>
            <p>{p.manager_name}{p.target_date && ` · due ${formatDay(p.target_date)}`}</p>
            <div className="progress"><i style={{ width: `${p.progress.percent}%` }} /></div>
            <span className="subtle">{p.progress.done} of {p.progress.total} tasks done</span>
          </Link>
        ))}
      </div>
      {creating && (
        <Drawer title="New project" onClose={() => setCreating(false)}>
          <RecordEditor<Project> title="Project" fields={PROJECT_FIELDS} record={null} saveLabel="Create project"
            save={(payload) => createResource<Project>(ENDPOINTS.projects, membersPayload(payload))}
            onSaved={(p) => navigate(`/projects/${p.id}`)} />
        </Drawer>
      )}
    </>
  );
}
