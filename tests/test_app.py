import copy
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

import src.app as app_module


@pytest.fixture
def activities(monkeypatch):
    test_activities = copy.deepcopy(app_module.activities)
    monkeypatch.setattr(app_module, "activities", test_activities)
    return test_activities


@pytest.fixture
def client(activities):
    with TestClient(app_module.app) as test_client:
        yield test_client


def signup_url(activity_name):
    return f"/activities/{quote(activity_name, safe='')}/signup"


def test_get_activities_returns_data_without_cache(client, activities):
    # Arrange
    expected_participants = activities["Chess Club"]["participants"]

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["Chess Club"]["participants"] == expected_participants


def test_signup_adds_participant(client, activities):
    # Arrange
    activity_name = "Chess Club"
    email = "new-student@example.edu"
    original_count = len(activities[activity_name]["participants"])

    # Act
    response = client.post(signup_url(activity_name), params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for {activity_name}"}
    assert activities[activity_name]["participants"].count(email) == 1
    assert len(activities[activity_name]["participants"]) == original_count + 1


def test_signup_rejects_duplicate_participant(client, activities):
    # Arrange
    activity_name = "Chess Club"
    email = "existing-student@example.edu"
    activities[activity_name]["participants"].append(email)

    # Act
    response = client.post(signup_url(activity_name), params={"email": email})

    # Assert
    assert response.status_code == 409
    assert response.json()["detail"] == "Student is already signed up for this activity"
    assert activities[activity_name]["participants"].count(email) == 1


def test_signup_returns_404_for_unknown_activity(client):
    # Arrange
    activity_name = "Unknown Club"

    # Act
    response = client.post(signup_url(activity_name), params={"email": "student@example.edu"})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_removes_participant(client, activities):
    # Arrange
    activity_name = "Chess Club"
    email = "existing-student@example.edu"
    activities[activity_name]["participants"].append(email)

    # Act
    response = client.delete(signup_url(activity_name), params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Unregistered {email} from {activity_name}"}
    assert email not in activities[activity_name]["participants"]


def test_unregister_returns_404_for_unknown_activity(client):
    # Arrange
    activity_name = "Unknown Club"

    # Act
    response = client.delete(signup_url(activity_name), params={"email": "student@example.edu"})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_returns_404_for_unregistered_email(client, activities):
    # Arrange
    activity_name = "Chess Club"
    email = "not-registered@example.edu"
    original_participants = activities[activity_name]["participants"].copy()

    # Act
    response = client.delete(signup_url(activity_name), params={"email": email})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"
    assert activities[activity_name]["participants"] == original_participants