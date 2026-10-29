import pytest

from helprequests.models import HelpRequests
from reports.models import AuditEvent
from solutions.models import Article

URL = "/api/solutions/articles/"
pytestmark = pytest.mark.django_db


@pytest.fixture
def people(make_user, network_team):
    tech = make_user("tech", "Technician")
    network_team.members.add(tech)
    return {"tech": tech, "manager": make_user("boss", "Manager"), "requester": make_user("req", "Requester"),
            "auditor": make_user("aud", "Auditor"), "outsider": make_user("outsider", "Technician"), "group": network_team}


@pytest.fixture
def articles(people):
    def make(title, status, visibility, **extra):
        return Article.objects.create(title=title, body=f"{title} body", status=status, visibility=visibility,
                                      author=people["tech"], **extra)
    S, V = Article.Status, Article.Visibility
    return {
        "public": make("Reset your VPN token", S.PUBLISHED, V.PUBLIC, keywords="error 809"),
        "internal": make("Restart the VPN concentrator", S.PUBLISHED, V.INTERNAL),
        "draft": make("Printer driver workaround", S.DRAFT, V.PUBLIC),
        "retired": make("Old Wi-Fi setup", S.RETIRED, V.PUBLIC),
    }


def titles(response):
    return {a["title"] for a in response.data["results"]}


@pytest.mark.parametrize("who,expected", [
    ("requester", {"public"}),
    ("tech", {"public", "internal", "draft", "retired"}),
    ("auditor", {"public", "internal", "draft", "retired"}),
])
def test_who_sees_which_articles(people, articles, client_for, who, expected):
    client = client_for(people[who])
    assert titles(client.get(URL)) == {articles[k].title for k in expected}
    for key, article in articles.items():
        assert client.get(f"{URL}{article.pk}/").status_code == (200 if key in expected else 404), key


def test_search_matches_body_and_keywords_but_respects_visibility(people, articles, client_for):
    requester = client_for(people["requester"])
    assert titles(requester.get(URL, {"search": "809"})) == {articles["public"].title}
    assert titles(requester.get(URL, {"search": "concentrator body"})) == set()
    assert titles(client_for(people["tech"]).get(URL, {"search": "concentrator body"})) == {articles["internal"].title}


def test_technicians_write_drafts_and_managers_publish(people, client_for):
    tech, manager = client_for(people["tech"]), client_for(people["manager"])
    draft = {"title": "Clear the Teams cache", "body": "Quit Teams, delete the cache folder.", "visibility": "public"}

    assert tech.post(URL, {**draft, "status": "published"}, format="json").status_code == 403
    created = tech.post(URL, draft, format="json")
    assert created.status_code == 201, created.data
    article = created.data
    assert article["number"].startswith("KB-") and article["status"] == "draft"
    assert article["author"] == people["tech"].pk and article["published_at"] is None

    assert tech.patch(f"{URL}{article['id']}/", {"summary": "Fixes sign-in loops"}, format="json").status_code == 200
    assert tech.patch(f"{URL}{article['id']}/", {"status": "published"}, format="json").status_code == 403

    published = manager.patch(f"{URL}{article['id']}/", {"status": "published"}, format="json")
    assert published.status_code == 200 and published.data["published_at"] is not None
    # Published content is now locked for technicians.
    assert tech.patch(f"{URL}{article['id']}/", {"body": "changed"}, format="json").status_code == 403
    assert AuditEvent.objects.filter(activity_type="article.updated").count() == 2


@pytest.mark.parametrize("who", ["requester", "auditor"])
def test_non_staff_cannot_write(people, client_for, who):
    client = client_for(people[who])
    assert client.post(URL, {"title": "x", "body": "y"}, format="json").status_code == 403


def test_articles_are_retired_not_deleted(people, articles, client_for):
    assert client_for(people["manager"]).delete(f"{URL}{articles['public'].pk}/").status_code == 405


class TestTicketLinks:
    @pytest.fixture
    def ticket(self, people):
        return HelpRequests.objects.create(requester=people["requester"], subject="VPN fails", description="d",
                                           assignment_group=people["group"])

    def url(self, ticket):
        return f"/api/help-requests/{ticket.public_id}/articles/"

    def test_staff_link_published_articles_and_requesters_see_only_public_ones(self, people, articles, ticket, client_for):
        tech = client_for(people["tech"])
        for key in ("public", "internal"):
            assert tech.post(self.url(ticket), {"article": articles[key].pk}, format="json").status_code == 200
        assert {a["title"] for a in tech.get(self.url(ticket)).data} == {articles["public"].title, articles["internal"].title}
        requester_view = client_for(people["requester"]).get(self.url(ticket)).data
        assert [a["title"] for a in requester_view] == [articles["public"].title]
        assert AuditEvent.objects.filter(activity_type="ticket.article_linked").count() == 2

        unlinked = tech.post(self.url(ticket), {"article": articles["internal"].pk, "unlink": True}, format="json")
        assert [a["title"] for a in unlinked.data] == [articles["public"].title]

    def test_only_published_articles_can_be_linked(self, people, articles, ticket, client_for):
        response = client_for(people["tech"]).post(self.url(ticket), {"article": articles["draft"].pk}, format="json")
        assert response.status_code == 400
        assert not ticket.articles.exists()

    def test_requesters_and_outsiders_cannot_link(self, people, articles, ticket, client_for):
        payload = {"article": articles["public"].pk}
        assert client_for(people["requester"]).post(self.url(ticket), payload, format="json").status_code == 403
        assert client_for(people["outsider"]).post(self.url(ticket), payload, format="json").status_code == 404
        assert not ticket.articles.exists()


class TestSuggestions:
    URL = f"{URL}suggest/"

    def suggested(self, client, q):
        response = client.get(self.URL, {"q": q})
        assert response.status_code == 200
        return [a["title"] for a in response.data]

    def test_any_word_may_match_and_requesters_only_get_public_published(self, people, articles, client_for):
        # "keeps" and "dropping" appear nowhere; "vpn" is enough.
        assert self.suggested(client_for(people["requester"]), "VPN keeps dropping") == [articles["public"].title]
        staff = set(self.suggested(client_for(people["tech"]), "VPN keeps dropping"))
        assert staff == {articles["public"].title, articles["internal"].title}  # never drafts or retired ones

    def test_words_are_stemmed_and_title_matches_rank_first(self, people, client_for):
        S, V = Article.Status.PUBLISHED, Article.Visibility.PUBLIC
        Article.objects.create(title="Clear a paper jam", body="Printers jam when the tray is overfilled.",
                               status=S, visibility=V, author=people["tech"])
        Article.objects.create(title="Printer shows offline", body="Restart the spooler.", status=S, visibility=V,
                               author=people["tech"])
        # The plural matches the singular title, and a title match outranks a body-only one.
        assert self.suggested(client_for(people["requester"]), "printers") == [
            "Printer shows offline", "Clear a paper jam"]

    @pytest.mark.parametrize("q", ["", "a b", "vpn & | ! :* <-> (", "'; drop table x; --"])
    def test_short_or_hostile_input_is_harmless(self, people, articles, client_for, q):
        titles = self.suggested(client_for(people["requester"]), q)
        assert titles in ([], [articles["public"].title])


class TestFeedback:
    def vote(self, client, article, helpful):
        return client.post(f"{URL}{article.pk}/feedback/", {"helpful": helpful}, format="json")

    def test_one_vote_per_person_and_counts_only_for_staff(self, people, articles, client_for):
        requester, article = client_for(people["requester"]), articles["public"]
        response = self.vote(requester, article, True)
        assert response.status_code == 200
        assert response.data["my_feedback"] is True and "helpful_count" not in response.data
        self.vote(client_for(people["tech"]), article, False)
        self.vote(requester, article, False)  # changes the vote rather than adding one

        staff_view = client_for(people["manager"]).get(f"{URL}{article.pk}/").data
        assert (staff_view["helpful_count"], staff_view["not_helpful_count"], staff_view["my_feedback"]) == (0, 2, None)
        assert client_for(people["auditor"]).get(f"{URL}{article.pk}/").data["not_helpful_count"] == 2

    def test_who_can_vote_on_what(self, people, articles, client_for):
        assert self.vote(client_for(people["auditor"]), articles["public"], True).status_code == 403
        assert self.vote(client_for(people["requester"]), articles["internal"], True).status_code == 404
        assert self.vote(client_for(people["tech"]), articles["draft"], True).status_code == 400
        assert self.vote(client_for(people["tech"]), articles["internal"], True).status_code == 200

    def test_staff_can_find_the_least_helpful_articles(self, people, articles, client_for):
        for who in ("requester", "tech", "manager"):
            self.vote(client_for(people[who]), articles["public"], False)
        self.vote(client_for(people["tech"]), articles["internal"], False)
        listed = client_for(people["manager"]).get(URL, {"ordering": "-not_helpful_count"}).data["results"]
        assert [a["title"] for a in listed[:2]] == [articles["public"].title, articles["internal"].title]
