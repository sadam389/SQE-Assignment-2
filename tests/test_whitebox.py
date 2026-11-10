import pytest
import registration
from registration import Student, Course, registration_decision, register_course

def create_student(**kwargs):
    defaults = dict(student_id="S001", completed_courses=set(), current_credits=0, outstanding_dues=0, registered_courses=set())
    defaults.update(kwargs)
    return Student(**defaults)

def create_course(**kwargs):
    defaults = dict(code="CS201", credit_hours=3, capacity=30, enrolled=0, prerequisites=set(), waitlist=[])
    defaults.update(kwargs)
    return Course(**defaults)

# TARGET: Line 51 (DUES_BLOCK return)
# Rationale: Black-box tests used dues=1 which bypassed this due to a defect.
# This structural test uses 1001 to satisfy the code's logic and cover the line.
def test_wb_line51_dues_block_uncovered():
    s = create_student(outstanding_dues=1001)
    c = create_course()
    assert registration_decision(s, c) == "DUES_BLOCK"

# TARGET: Line 71 (waitlist append)
# Rationale: The defect prevents "WAITLISTED" from ever being returned.
# We use monkeypatch to simulate the correct decision and test the state change logic.
def test_wb_line71_register_waitlist_branch(monkeypatch):
    # Force the decision to be WAITLISTED to execute the branch
    monkeypatch.setattr(registration, "registration_decision", lambda s, c: "WAITLISTED")
    s = create_student(student_id="S001")
    c = create_course(capacity=1, enrolled=1)
    
    result = register_course(s, c)
    assert result == "WAITLISTED"
    assert c.waitlist == ["S001"]
    assert s.current_credits == 0
    assert s.registered_courses == set()

# TARGET: Line 59 (WAITLISTED return) - Documenting Infeasibility
# Rationale: Line 59 is structurally unreachable. We document this by proving
# that the early validation (Line 48) catches the condition first and raises an error.
def test_wb_line59_unreachable_waitlisted():
    s = create_student()
    c = create_course(capacity=1, enrolled=2) # enrolled > capacity
    # It should raise ValueError (Line 49) instead of returning WAITLISTED (Line 59)
    with pytest.raises(ValueError, match="Invalid capacity or enrollment"):
        registration_decision(s, c)

# TARGET: MC/DC Conditions for Line 48
@pytest.mark.parametrize("enrolled, capacity, should_raise", [
    (-1, 1, True),  # Condition A is False
    (2, 1, True),   # Condition B is False (A is True)
    (0, 1, False),  # All conditions evaluated (A=True, B=True, C=False)
    (0, 0, True)    # Condition C is True
])
def test_wb_mcdc_condition_d2(enrolled, capacity, should_raise):
    s = create_student()
    c = create_course(enrolled=enrolled, capacity=capacity)
    
    if should_raise:
        with pytest.raises(ValueError):
            registration_decision(s, c)
    else:
        assert registration_decision(s, c) == "REGISTERED"