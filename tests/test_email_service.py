from services import email_service


def test_build_submission_email_includes_submission_details(monkeypatch):
    monkeypatch.setitem(email_service.env_data, "SMTP_FROM_EMAIL", "noreply@example.com")

    message = email_service._build_submission_email(
        tournament={"title": "Spring Cup"},
        organizer={"email": "organizer@example.com"},
        team={
            "full_name": "Team Rocket",
            "email": "team@example.com",
        },
        submission={
            "repository_url": "https://github.com/team/project",
            "video_demo_url": "https://video.example/demo",
            "live_demo_url": "https://demo.example",
            "description": "Ready for review",
            "submitted_at": 1710000000,
        },
    )

    body = message.get_content()
    assert message["To"] == "organizer@example.com"
    assert message["Subject"] == "New submission for Spring Cup"
    assert "Tournament: Spring Cup" in body
    assert "Team: Team Rocket" in body
    assert "Team email: team@example.com" in body
    assert "Repository: https://github.com/team/project" in body
    assert "Demo video: https://video.example/demo" in body
    assert "Live demo: https://demo.example" in body
    assert "Ready for review" in body
    assert "Submitted at:" in body
