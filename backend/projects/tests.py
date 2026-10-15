import pytest

from projects.models import Project, ProjectMember, ProjectTask


@pytest.fixture
def setup(make_user):
    pm = make_user("pm", "Manager")
    dev = make_user("dev", "Technician")
    viewer = make_user("viewer", "Requester")
    stranger = make_user("stranger", "Technician")
    project = Project.objects.create(key="NET", name="Network refresh", manager=pm)
    ProjectMember.objects.create(project=project, user=dev, role="contributor")
    ProjectMember.objects.create(project=project, user=viewer, role="viewer")
    return {"pm": pm, "dev": dev, "viewer": viewer, "stranger": stranger, "project": project}


@pytest.mark.django_db
def test_only_managers_create_projects(setup, client_for):
    data = {"key": "ERP", "name": "ERP", "manager": setup["dev"].pk}
    assert client_for(setup["dev"]).post("/api/projects/items/", data, format="json").status_code == 403
    assert client_for(setup["pm"]).post("/api/projects/items/", data, format="json").status_code == 201


@pytest.mark.django_db
def test_visibility_follows_membership(setup, client_for):
    assert client_for(setup["stranger"]).get(f"/api/projects/items/{setup['project'].pk}/").status_code == 404
    assert client_for(setup["viewer"]).get(f"/api/projects/items/{setup['project'].pk}/").status_code == 200


@pytest.mark.django_db
def test_task_permissions_and_numbering(setup, client_for):
    project = setup["project"]
    task_data = {"project": project.pk, "title": "Order switches", "assignee": setup["dev"].pk}
    assert client_for(setup["viewer"]).post("/api/projects/tasks/", task_data, format="json").status_code == 403
    assert client_for(setup["stranger"]).post("/api/projects/tasks/", task_data, format="json").status_code == 400
    created = client_for(setup["dev"]).post("/api/projects/tasks/", task_data, format="json")
    assert created.status_code == 201, created.data
    assert created.data["number"] == "NET-1"
    second = client_for(setup["dev"]).post("/api/projects/tasks/", {**task_data, "title": "Install"}, format="json")
    assert second.data["number"] == "NET-2"
    outsider_assign = client_for(setup["dev"]).post("/api/projects/tasks/", {**task_data, "assignee": setup["stranger"].pk}, format="json")
    assert outsider_assign.status_code == 400


@pytest.mark.django_db
def test_dependencies_block_completion_and_cycles(setup, client_for):
    project = setup["project"]
    a = ProjectTask.objects.create(project=project, number="NET-1", title="A")
    b = ProjectTask.objects.create(project=project, number="NET-2", title="B")
    dev = client_for(setup["dev"])
    assert dev.patch(f"/api/projects/tasks/{b.pk}/", {"depends_on": [a.pk]}, format="json").status_code == 200
    assert dev.patch(f"/api/projects/tasks/{a.pk}/", {"depends_on": [b.pk]}, format="json").status_code == 400  # cycle
    assert dev.patch(f"/api/projects/tasks/{b.pk}/", {"status": "done"}, format="json").status_code == 400  # A not done
    assert dev.patch(f"/api/projects/tasks/{a.pk}/", {"status": "done"}, format="json").status_code == 200
    assert dev.patch(f"/api/projects/tasks/{b.pk}/", {"status": "done"}, format="json").status_code == 200


@pytest.mark.django_db
def test_assignee_viewer_can_update_own_status_only(setup, client_for):
    task = ProjectTask.objects.create(project=setup["project"], number="NET-1", title="Review", assignee=setup["viewer"])
    viewer = client_for(setup["viewer"])
    assert viewer.patch(f"/api/projects/tasks/{task.pk}/", {"status": "in_progress"}, format="json").status_code == 200
    assert viewer.patch(f"/api/projects/tasks/{task.pk}/", {"title": "Renamed"}, format="json").status_code == 403


@pytest.mark.django_db
def test_only_project_manager_edits_project(setup, client_for):
    url = f"/api/projects/items/{setup['project'].pk}/"
    assert client_for(setup["dev"]).patch(url, {"name": "Mine now"}, format="json").status_code == 403
    assert client_for(setup["pm"]).patch(url, {"status": "completed"}, format="json").data["completed_at"] is not None
