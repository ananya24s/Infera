import pytest

from app.agents.query_planning import question_to_hypothesis


@pytest.mark.parametrize(
    "question, expected",
    [
        ("Does creatine supplementation improve cognitive performance?", "Creatine supplementation improves cognitive performance."),
        ("Is intermittent fasting effective for long-term weight loss?", "Intermittent fasting is effective for long-term weight loss."),
        ("Do statins reduce cardiovascular risk in healthy adults?", "Statins reduce cardiovascular risk in healthy adults."),
        ("Does screen time before bed impair sleep quality?", "Screen time before bed impairs sleep quality."),
        ("Can meditation lower blood pressure?", "Meditation can lower blood pressure."),
        ("Are electric cars safer than gasoline cars?", "Electric cars are safer than gasoline cars."),
    ],
)
def test_yes_no_questions_become_statements(question, expected):
    assert question_to_hypothesis(question) == expected


def test_unrecognised_shape_falls_back_to_the_question_text():
    assert question_to_hypothesis("What causes migraines?") == "What causes migraines."
