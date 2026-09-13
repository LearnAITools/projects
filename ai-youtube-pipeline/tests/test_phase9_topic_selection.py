from app.automation.automation_manager import AutomationManager
from app.automation.topic_selector import TopicSelector


def test_topic_selector_skips_duplicate_topics(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    manager.history.record(job_id="job_001", topic="AI tools", status="COMPLETED")

    selector = TopicSelector(history_manager=manager)
    chosen = selector.pick_topic(["AI tools", "Prompt engineering", "LLM workflows"])

    assert chosen == "Prompt engineering"


def test_topic_selector_returns_first_option_when_no_duplicates(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    selector = TopicSelector(history_manager=manager)

    chosen = selector.pick_topic(["AI tools", "LLM workflows"])

    assert chosen == "AI tools"


def test_topic_selector_raises_when_no_topics_available(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    manager.history.record(job_id="job_001", topic="AI tools", status="COMPLETED")
    selector = TopicSelector(history_manager=manager)

    try:
        selector.pick_topic(["AI tools"])
        assert False, "Expected ValueError for no selectable topics"
    except ValueError:
        pass
