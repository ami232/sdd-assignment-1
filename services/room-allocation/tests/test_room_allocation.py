"""Tests for the Room Allocation domain.

Trip Management is replaced by the `trips` fake from conftest.py, so these
tests check room rules only. Waitlist promotion after a cancellation is a
Trip Management rule and is tested in that service.
"""

import pytest

from room_allocation import (
    add_roommate_preference,
    assign_student,
    check_room_on_trip,
    create_room,
    get_rooms,
    release_student,
    remove_assignment,
)


def test_create_room(test_db, trips):
    trip_id = trips.add_trip()
    room_id = create_room(trip_id, "Room 101", 4)

    assert room_id == 1
    assert get_rooms(trip_id) == [
        {"id": 1, "name": "Room 101", "capacity": 4, "occupied": 0}
    ]


def test_reject_invalid_room_capacity(test_db, trips):
    trip_id = trips.add_trip()

    with pytest.raises(ValueError):
        create_room(trip_id, "Too large", 7)

    with pytest.raises(ValueError):
        create_room(trip_id, "Too small", 0)


def test_reject_unknown_trip(test_db, trips):
    with pytest.raises(ValueError, match="Trip not found"):
        create_room(999, "Room 101", 4)


def test_reject_duplicate_room_name(test_db, trips):
    trip_id = trips.add_trip()
    create_room(trip_id, "Room 101", 4)

    with pytest.raises(ValueError):
        create_room(trip_id, "Room 101", 4)


def test_reject_empty_room_name(test_db, trips):
    trip_id = trips.add_trip()

    with pytest.raises(ValueError):
        create_room(trip_id, "   ", 4)


def test_assign_confirmed_student(test_db, trips):
    trip_id = trips.add_trip()
    room_id = create_room(trip_id, "Room 101", 2)
    student_id = trips.add_student(trip_id)

    assignment_id = assign_student(room_id, student_id)

    assert assignment_id == 1
    assert get_rooms(trip_id)[0]["occupied"] == 1


def test_reject_unpaid_student(test_db, trips):
    trip_id = trips.add_trip()
    room_id = create_room(trip_id, "Room 101", 2)
    student_id = trips.add_student(trip_id, status="pending_payment")

    with pytest.raises(ValueError, match="confirmed"):
        assign_student(room_id, student_id)


def test_reject_full_room(test_db, trips):
    trip_id = trips.add_trip()
    room_id = create_room(trip_id, "Room 101", 1)
    sofia = trips.add_student(trip_id)
    emma = trips.add_student(trip_id)

    assign_student(room_id, sofia)

    with pytest.raises(ValueError, match="full"):
        assign_student(room_id, emma)


def test_reject_double_assignment(test_db, trips):
    trip_id = trips.add_trip()
    room_one = create_room(trip_id, "Room 101", 2)
    room_two = create_room(trip_id, "Room 102", 2)
    sofia = trips.add_student(trip_id)

    assign_student(room_one, sofia)

    with pytest.raises(ValueError, match="already has a room"):
        assign_student(room_two, sofia)


def test_reject_different_trip(test_db, trips):
    first_trip = trips.add_trip()
    second_trip = trips.add_trip()
    room_id = create_room(first_trip, "Room 101", 2)
    student_id = trips.add_student(second_trip)

    with pytest.raises(ValueError, match="different trips"):
        assign_student(room_id, student_id)


def test_reject_unknown_room_or_registration(test_db, trips):
    trip_id = trips.add_trip()
    room_id = create_room(trip_id, "Room 101", 4)
    student = trips.add_student(trip_id)

    with pytest.raises(ValueError, match="Room not found"):
        assign_student(999, student)

    with pytest.raises(ValueError, match="Registration not found"):
        assign_student(room_id, 999)


def test_remove_assignment_frees_bed(test_db, trips):
    trip_id = trips.add_trip()
    room_id = create_room(trip_id, "Room 101", 1)
    sofia = trips.add_student(trip_id)

    assign_student(room_id, sofia)

    assert remove_assignment(sofia) is True
    assert get_rooms(trip_id)[0]["occupied"] == 0
    assert remove_assignment(sofia) is False


def test_add_roommate_preference(test_db, trips):
    trip_id = trips.add_trip()
    sofia = trips.add_student(trip_id)
    emma = trips.add_student(trip_id)

    assert add_roommate_preference(sofia, emma) == 1


def test_reject_self_preference(test_db, trips):
    trip_id = trips.add_trip()
    sofia = trips.add_student(trip_id)

    with pytest.raises(ValueError):
        add_roommate_preference(sofia, sofia)


def test_reject_duplicate_preference(test_db, trips):
    trip_id = trips.add_trip()
    sofia = trips.add_student(trip_id)
    emma = trips.add_student(trip_id)

    add_roommate_preference(sofia, emma)

    with pytest.raises(ValueError):
        add_roommate_preference(sofia, emma)


def test_reject_roommate_from_another_trip(test_db, trips):
    sofia = trips.add_student(trips.add_trip())
    emma = trips.add_student(trips.add_trip())

    with pytest.raises(ValueError, match="same trip"):
        add_roommate_preference(sofia, emma)


def test_reject_unpaid_roommate_preference(test_db, trips):
    trip_id = trips.add_trip()
    sofia = trips.add_student(trip_id)
    emma = trips.add_student(trip_id, status="pending_payment")

    with pytest.raises(ValueError, match="confirmed"):
        add_roommate_preference(sofia, emma)


def test_reject_preference_for_unknown_student(test_db, trips):
    student = trips.add_student(trips.add_trip())

    with pytest.raises(ValueError, match="Both registrations must exist"):
        add_roommate_preference(student, 999)


def test_get_rooms_for_unknown_trip(test_db, trips):
    with pytest.raises(ValueError, match="Trip not found"):
        get_rooms(999)


def test_check_room_on_trip(test_db, trips):
    trip_id = trips.add_trip()
    room_id = create_room(trip_id, "Room 101", 2)

    check_room_on_trip(trip_id, room_id)

    with pytest.raises(ValueError, match="not found on this trip"):
        check_room_on_trip(trip_id + 1, room_id)


def test_release_student_frees_bed(test_db, trips):
    trip_id = trips.add_trip()
    room_id = create_room(trip_id, "Room 101", 2)
    sofia = trips.add_student(trip_id)
    assign_student(room_id, sofia)

    release_student(sofia)

    assert get_rooms(trip_id)[0]["occupied"] == 0


def test_release_student_removes_roommate_preferences(test_db, trips):
    trip_id = trips.add_trip()
    ana = trips.add_student(trip_id)
    ben = trips.add_student(trip_id)
    cara = trips.add_student(trip_id)

    add_roommate_preference(ana, ben)
    add_roommate_preference(cara, ana)
    add_roommate_preference(ben, cara)

    release_student(ana)

    # Both requests involving Ana are gone; Ben's request for Cara stays.
    remaining = test_db.execute(
        """
        SELECT registration_id, preferred_registration_id
        FROM roommate_preferences
        """
    ).fetchall()

    assert [tuple(row) for row in remaining] == [(ben, cara)]


def test_release_student_twice_is_harmless(test_db, trips):
    sofia = trips.add_student(trips.add_trip())

    release_student(sofia)
    release_student(sofia)
