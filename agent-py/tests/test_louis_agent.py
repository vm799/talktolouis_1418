"""Unit tests for LouisAgent business logic.

Tests mock LouisService to isolate agent routing decisions.
No LiveKit session required — tests call the service methods directly.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_mongo_repo():
    repo = AsyncMock()
    repo.insert_event = AsyncMock(return_value="fake_id")
    return repo


@pytest.fixture
def louis_service(mock_mongo_repo):
    from louis_service import LouisService
    return LouisService(mongo_repo=mock_mongo_repo)


class TestLouisServiceGreeting:
    async def test_greeting_returns_tuple(self, louis_service):
        response, should_escalate = await louis_service.greeting(
            session_id="sess_001", user_id="user_1"
        )
        assert isinstance(response, str)
        assert len(response) > 0
        assert should_escalate is False

    async def test_greeting_logs_event(self, louis_service, mock_mongo_repo):
        await louis_service.greeting(session_id="sess_001", user_id="user_1")
        mock_mongo_repo.insert_event.assert_called_once()

    async def test_greeting_contains_citation(self, louis_service):
        response, _ = await louis_service.greeting(
            session_id="sess_001", user_id="user_1"
        )
        assert "NICE" in response or "NHS" in response


class TestLouisServiceAssessQuestion:
    async def test_safe_question_returns_no_escalation(self, louis_service):
        response, should_escalate = await louis_service.assess_question(
            session_id="sess_001",
            user_id="user_1",
            user_input="What happens next with my results?",
        )
        assert isinstance(response, str)
        assert should_escalate is False

    async def test_red_flag_triggers_escalation(self, louis_service):
        response, should_escalate = await louis_service.assess_question(
            session_id="sess_001",
            user_id="user_1",
            user_input="I have flashing lights in my vision",
        )
        assert should_escalate is True
        assert "111" in response or "999" in response

    async def test_response_is_safe_no_diagnosis(self, louis_service):
        from response_templates import is_safe_response
        response, _ = await louis_service.assess_question(
            session_id="sess_001",
            user_id="user_1",
            user_input="Am I going blind?",
        )
        assert is_safe_response(response) is True

    async def test_anxiety_question_returns_reassurance(self, louis_service):
        response, should_escalate = await louis_service.assess_question(
            session_id="sess_001",
            user_id="user_1",
            user_input="I am really worried and scared",
        )
        assert should_escalate is False
        assert isinstance(response, str)


class TestLouisServiceEscalate:
    async def test_escalate_returns_nhs_text(self, louis_service):
        response = await louis_service.escalate(
            session_id="sess_001",
            user_id="user_1",
            reason="curtain_vision",
        )
        assert "111" in response or "999" in response

    async def test_escalate_logs_event(self, louis_service, mock_mongo_repo):
        await louis_service.escalate(
            session_id="sess_001", user_id="user_1", reason="pain_in_eye"
        )
        # escalate() logs two events: the escalation itself + a task_pending
        # marker so the coordination engine tracks awaiting specialist review.
        assert mock_mongo_repo.insert_event.call_count == 2
        event_types = [
            c.args[0].event_type for c in mock_mongo_repo.insert_event.call_args_list
        ]
        assert "escalation" in event_types
        assert "task_pending" in event_types


class TestRedFlagDetector:
    def test_flashing_lights_is_red_flag(self):
        from louis.red_flag_detector import RedFlagDetector
        assert RedFlagDetector.check("I see flashing lights") is True

    def test_normal_question_not_red_flag(self):
        from louis.red_flag_detector import RedFlagDetector
        assert RedFlagDetector.check("What happens at my next appointment?") is False

    def test_none_input_not_red_flag(self):
        from louis.red_flag_detector import RedFlagDetector
        assert RedFlagDetector.check(None) is False

    def test_empty_string_not_red_flag(self):
        from louis.red_flag_detector import RedFlagDetector
        assert RedFlagDetector.check("") is False

    def test_curtain_is_red_flag(self):
        from louis.red_flag_detector import RedFlagDetector
        assert RedFlagDetector.check("I have a curtain over my eye") is True

    def test_sudden_vision_loss_is_red_flag(self):
        from louis.red_flag_detector import RedFlagDetector
        assert RedFlagDetector.check("sudden vision loss in left eye") is True

    def test_case_insensitive(self):
        from louis.red_flag_detector import RedFlagDetector
        assert RedFlagDetector.check("EMERGENCY HELP") is True


class TestLouisAgentWiring:
    async def test_louis_agent_instantiates(self, mock_mongo_repo):
        from agents.louis_agent import LouisAgent
        from louis_service import LouisService
        service = LouisService(mongo_repo=mock_mongo_repo)
        agent = LouisAgent(
            session_id="sess_001",
            user_id="user_1",
            tenant_id="default",
            louis_service=service,
        )
        assert agent is not None

    async def test_handle_patient_input_safe_question(self, mock_mongo_repo):
        from agents.louis_agent import LouisAgent
        from louis_service import LouisService
        service = LouisService(mongo_repo=mock_mongo_repo)
        agent = LouisAgent(
            session_id="sess_001",
            user_id="user_1",
            tenant_id="default",
            louis_service=service,
        )
        mock_context = MagicMock()
        response = await agent.handle_patient_input(mock_context, "What happens next?")
        assert isinstance(response, str)
        assert len(response) > 0

    async def test_handle_patient_input_red_flag_sets_escalated(self, mock_mongo_repo):
        from agents.louis_agent import LouisAgent
        from louis_service import LouisService
        service = LouisService(mongo_repo=mock_mongo_repo)
        agent = LouisAgent(
            session_id="sess_001",
            user_id="user_1",
            tenant_id="default",
            louis_service=service,
        )
        mock_context = MagicMock()
        response = await agent.handle_patient_input(
            mock_context, "I have flashing lights and pain"
        )
        assert agent._escalated is True
        assert "111" in response or "999" in response

    async def test_after_escalation_always_returns_emergency_text(self, mock_mongo_repo):
        from agents.louis_agent import LouisAgent
        from louis_service import LouisService
        service = LouisService(mongo_repo=mock_mongo_repo)
        agent = LouisAgent(
            session_id="sess_001",
            user_id="user_1",
            tenant_id="default",
            louis_service=service,
        )
        agent._escalated = True
        mock_context = MagicMock()
        response = await agent.handle_patient_input(mock_context, "anything")
        assert "111" in response or "999" in response
