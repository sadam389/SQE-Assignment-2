import pytest
from registration import (
    Student, Course, check_credit_limit, prerequisites_satisfied,
    registration_decision, register_course, withdraw_course
)

# --- Helper functions to create fresh objects for each test ---
def create_student(**kwargs):
    defaults = dict(student_id="S001", completed_courses=set(), current_credits=0, outstanding_dues=0, registered_courses=set())
    defaults.update(kwargs)
    return Student(**defaults)

def create_course(**kwargs):
    defaults = dict(code="CS201", credit_hours=3, capacity=30, enrolled=0, prerequisites=set(), waitlist=[])
    defaults.update(kwargs)
    return Course(**defaults)

# ==========================================
# ECP & BVA: Credit Hours
# ==========================================
def test_ecp01_bva09_exact_18_allowed():
    # ECP-01, BVA-09: FR-01 exact total 18 must be allowed.
    assert check_credit_limit(15, 3) is True

def test_ecp02_over_18_rejected():
    # ECP-02: FR-01 total 19 is over limit.
    assert check_credit_limit(16, 3) is False

@pytest.mark.parametrize("current, message", [(-1, "Invalid current credits"), (19, "Invalid current credits")])
def test_ecp03_ecp04_bva03_bva04_invalid_current(current, message):
    # ECP-03, ECP-04, BVA-03, BVA-04
    with pytest.raises(ValueError, match=message):
        check_credit_limit(current, 1)

@pytest.mark.parametrize("new, message", [(0, "Invalid course credits"), (5, "Invalid course credits")])
def test_ecp05_ecp06_bva07_bva08_invalid_new_credits(new, message):
    # ECP-05, ECP-06, BVA-07, BVA-08
    with pytest.raises(ValueError, match=message):
        check_credit_limit(0, new)

def test_bva01_current_min_valid():
    assert check_credit_limit(0, 3) is True

def test_bva02_current_max_valid_but_total_over():
    assert check_credit_limit(18, 1) is False

def test_bva05_bva06_new_credits_valid_range():
    assert check_credit_limit(10, 1) is True
    assert check_credit_limit(10, 4) is True

def test_bva10_combined_just_over_18():
    assert check_credit_limit(17, 2) is False

# ==========================================
# ECP & BVA: Dues
# ==========================================
def test_ecp07_dues_zero_not_blocked():
    # BVA-11
    assert registration_decision(create_student(outstanding_dues=0), create_course()) == "REGISTERED"

def test_ecp08_bva12_dues_one_blocks():
    # ECP-08, BVA-12: FR-04 any positive dues must block.
    assert registration_decision(create_student(outstanding_dues=1), create_course()) == "DUES_BLOCK"

def test_ecp09_bva13_negative_dues_raises():
    with pytest.raises(ValueError, match="Invalid dues"):
        registration_decision(create_student(outstanding_dues=-1), create_course())

# ==========================================
# ECP: Prerequisites
# ==========================================
def test_ecp10_prereq_empty_true():
    assert prerequisites_satisfied(set(), set()) is True

def test_ecp11_prereq_all_true():
    assert prerequisites_satisfied({"CS101", "MATH101"}, {"CS101", "MATH101"}) is True

def test_ecp12_prereq_some_false():
    # FR-03: every required prerequisite must be completed.
    assert prerequisites_satisfied({"CS101"}, {"CS101", "MATH101"}) is False

def test_ecp13_prereq_none_false():
    assert prerequisites_satisfied(set(), {"CS101"}) is False

# ==========================================
# ECP & BVA: Availability
# ==========================================
def test_ecp14_bva14_seat_available_registered():
    assert registration_decision(create_student(), create_course(capacity=1, enrolled=0)) == "REGISTERED"

def test_ecp15_bva15_full_course_waitlisted():
    # ECP-15, BVA-15: FR-08 enrolled == capacity -> WAITLISTED.
    assert registration_decision(create_student(), create_course(capacity=1, enrolled=1)) == "WAITLISTED"

@pytest.mark.parametrize("capacity, enrolled", [(0, 0), (1, -1), (1, 2)])
def test_ecp16_bva16_bva17_bva18_invalid_capacity(capacity, enrolled):
    with pytest.raises(ValueError, match="Invalid capacity or enrollment"):
        registration_decision(create_student(), create_course(capacity=capacity, enrolled=enrolled))

# ==========================================
# ECP & Decision Table: Logic Priority
# ==========================================
def test_ecp17_dt02_already_registered():
    s = create_student(registered_courses={"CS201"})
    assert registration_decision(s, create_course(code="CS201")) == "ALREADY_REGISTERED"

def test_ecp18_dt03_prereq_missing():
    s = create_student(completed_courses={"CS101"})
    c = create_course(prerequisites={"CS101", "MATH101"})
    assert registration_decision(s, c) == "PREREQUISITES_MISSING"

def test_ecp19_dt04_credit_limit():
    s = create_student(current_credits=16)
    assert registration_decision(s, create_course(credit_hours=3)) == "CREDIT_LIMIT"

def test_dt07_dues_priority_over_already_registered():
    s = create_student(outstanding_dues=1, registered_courses={"CS201"})
    assert registration_decision(s, create_course(code="CS201")) == "DUES_BLOCK"

def test_dt08_already_registered_priority_over_prereq():
    s = create_student(registered_courses={"CS201"}, completed_courses=set())
    c = create_course(code="CS201", prerequisites={"MATH101"})
    assert registration_decision(s, c) == "ALREADY_REGISTERED"

def test_dt09_prereq_priority_over_credit_limit():
    s = create_student(current_credits=18, completed_courses=set())
    c = create_course(credit_hours=3, prerequisites={"MATH101"})
    assert registration_decision(s, c) == "PREREQUISITES_MISSING"

def test_dt10_credit_priority_over_availability():
    s = create_student(current_credits=18)
    c = create_course(credit_hours=3, capacity=1, enrolled=1)
    assert registration_decision(s, c) == "CREDIT_LIMIT"

# ==========================================
# State Changes (Register & Withdraw)
# ==========================================
def test_register_success_updates_state():
    s = create_student()
    c = create_course(capacity=2, enrolled=0)
    assert register_course(s, c) == "REGISTERED"
    assert s.registered_courses == {"CS201"}
    assert s.current_credits == 3
    assert c.enrolled == 1

def test_unsuccessful_registration_does_not_change_state():
    s = create_student(registered_courses={"CS201"}, current_credits=3)
    c = create_course(capacity=2, enrolled=1)
    # Before state
    before_courses = set(s.registered_courses)
    before_credits = s.current_credits
    before_enrolled = c.enrolled
    
    assert register_course(s, c) == "ALREADY_REGISTERED"
    
    # After state must be identical
    assert s.registered_courses == before_courses
    assert s.current_credits == before_credits
    assert c.enrolled == before_enrolled

def test_waitlisted_appends_once_without_other_state_change():
    s = create_student(student_id="S001")
    c = create_course(capacity=1, enrolled=1)
    
    assert register_course(s, c) == "WAITLISTED"
    assert c.waitlist == ["S001"]
    assert s.current_credits == 0
    assert s.registered_courses == set()
    assert c.enrolled == 1

def test_withdraw_registered_decrements_enrollment():
    s = create_student(registered_courses={"CS201"}, current_credits=3)
    c = create_course(code="CS201", credit_hours=3, capacity=2, enrolled=1)
    
    assert withdraw_course(s, c) is True
    assert s.registered_courses == set()
    assert s.current_credits == 0
    assert c.enrolled == 0  # FR-13 says this must decrement!

def test_withdraw_not_registered_no_change():
    s = create_student()
    c = create_course(capacity=2, enrolled=0)
    assert withdraw_course(s, c) is False
    assert s.registered_courses == set()
    assert s.current_credits == 0
    assert c.enrolled == 0