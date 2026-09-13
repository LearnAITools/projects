from app.automation.automation_manager import AutomationManager
from app.automation.topic_queue import TopicQueue


def test_topic_queue_skips_duplicate_topics(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    manager.history.record(job_id="job_001", topic="AI tools", status="COMPLETED")

    queue = TopicQueue(history_manager=manager)
    queue.add_topics(["AI tools", "Prompt engineering", "LLM workflows"])

    assert queue.next_topic() == "Prompt engineering"


def test_topic_queue_pops_topics_in_order(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    queue = TopicQueue(history_manager=manager)
    queue.add_topics(["AI tools", "Prompt engineering"])

    assert queue.next_topic() == "AI tools"
    assert queue.next_topic() == "Prompt engineering"


def test_topic_queue_raises_when_no_available_topics(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    manager.history.record(job_id="job_001", topic="AI tools", status="COMPLETED")
    queue = TopicQueue(history_manager=manager)
    queue.add_topics(["AI tools"])

    try:
        queue.next_topic()
        assert False, "Expected ValueError when all topics are unavailable"
    except ValueError:
        pass
