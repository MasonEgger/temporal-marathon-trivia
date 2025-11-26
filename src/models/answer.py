# ABOUTME: Answer-related models for submit_answer update handler.
# Contains request/response models for answer submission with type safety.

from dataclasses import dataclass

from src.models.question import Question


@dataclass
class SubmitAnswerRequest:
    """Request model for submit_answer update handler.

    Encapsulates all parameters needed to submit an answer, maintaining
    type safety when passing to workflow update handlers.

    Attributes:
        date: Date string in ISO format (e.g., "2025-03-10")
        question_id: ID of the question being answered
        answer_choice: Answer choice (must be "A", "B", "C", or "D")
        show_correct_answer: Whether to include correct answer in response

    Example:
        >>> request = SubmitAnswerRequest(
        ...     date="2025-03-10",
        ...     question_id="q1",
        ...     answer_choice="B",
        ...     show_correct_answer=False
        ... )
        >>> result = await handle.execute_update(
        ...     PlayerEntityWorkflow.submit_answer, request
        ... )
    """

    date: str
    question_id: str
    answer_choice: str
    show_correct_answer: bool


@dataclass
class AnswerResult:
    """Result returned from submit_answer update handler.

    Contains feedback about the submitted answer and what to display next
    (either the next question or a completion message).

    Attributes:
        is_correct: Whether the submitted answer was correct
        correct_answer: The correct answer (A/B/C/D), only if show_correct_answer is True
        next_question: The next question to display, or None if day complete
        completion_message: Message to display if day complete, or None if more questions
        current_score: Player's current score for this day
        total_questions: Total number of questions for this day

    Example:
        >>> # Correct answer with next question
        >>> result = AnswerResult(
        ...     is_correct=True,
        ...     correct_answer=None,  # Not showing correct answers
        ...     next_question=Question(...),
        ...     completion_message=None,
        ...     current_score=1,
        ...     total_questions=5
        ... )
        >>>
        >>> # Last question with completion
        >>> result = AnswerResult(
        ...     is_correct=True,
        ...     correct_answer=None,
        ...     next_question=None,
        ...     completion_message="Great job! You scored 5/5!",
        ...     current_score=5,
        ...     total_questions=5
        ... )
    """

    is_correct: bool
    correct_answer: str | None
    next_question: Question | None
    completion_message: str | None
    current_score: int
    total_questions: int
