#!/usr/bin/env python3
# scripts/generate_complete_data.py

import asyncio
import json
from datetime import datetime, timedelta
from bson import ObjectId

# Import necessary collections directly
from app.core.db import get_hours_collection, get_schedules_collection, get_timesheets_collection

# Store ID from your data
STORE_ID = "67ca013d2fb92168a3ba6463"

# Employee IDs from your data
MANAGER_ID = "67ca0793b4ff9d2a10d93245"  # Store Manager
CASHIER_ID = "67ca07bab4ff9d2a10d93247"  # Senior Cashier

# Convert these to user IDs for approvals
MANAGER_USER_ID = "67ca0569f53ddaa3f32589f2"
CASHIER_USER_ID = "67ca00f32fb92168a3ba6462"

# Generate date range for the test data
NOW = datetime.utcnow()
TODAY = NOW.replace(hour=0, minute=0, second=0, microsecond=0)
MONDAY_OF_WEEK = TODAY - timedelta(days=TODAY.weekday())
PREVIOUS_MONDAY = MONDAY_OF_WEEK - timedelta(days=7)

print(f"Generating test data for the week of {MONDAY_OF_WEEK.date()} and previous week {PREVIOUS_MONDAY.date()}")


async def generate_test_hours():
    """Generate test hour entries for the employees directly into the database"""
    hours_collection = get_hours_collection()
    hours_data = []

    # Generate hours for the previous week
    for employee_id in [MANAGER_ID, CASHIER_ID]:
        # Monday to Friday of previous week
        for day_offset in range(5):  # 0 = Monday, 4 = Friday
            work_day = PREVIOUS_MONDAY + timedelta(days=day_offset)

            # Morning shift
            clock_in = work_day.replace(hour=9, minute=0)
            clock_out = work_day.replace(hour=17, minute=30)

            # Break from 12-12:30
            break_start = work_day.replace(hour=12, minute=0)
            break_end = work_day.replace(hour=12, minute=30)

            # Calculate total minutes (excluding break)
            work_minutes = int((clock_out - clock_in).total_seconds() / 60)
            break_minutes = int((break_end - break_start).total_seconds() / 60)
            total_minutes = work_minutes - break_minutes

            # Create hour record document directly
            hour_data = {
                "employee_id": employee_id,
                "store_id": STORE_ID,
                "clock_in": clock_in,
                "clock_out": clock_out,
                "break_start": break_start,
                "break_end": break_end,
                "total_minutes": total_minutes,
                "status": "approved",  # Already approved for previous week
                "approved_by": MANAGER_USER_ID,
                "approved_at": datetime.utcnow(),
                "notes": f"Regular shift - {work_day.strftime('%A')}",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            # Insert directly into collection
            result = await hours_collection.insert_one(hour_data)
            if result.inserted_id:
                print(f"Created hour record for {employee_id} on {work_day.date()}")
                inserted_doc = await hours_collection.find_one({"_id": result.inserted_id})
                hours_data.append(inserted_doc)
            else:
                print(f"Failed to create hour record for {employee_id} on {work_day.date()}")

    # Generate hours for the current week (Monday to today)
    current_day_offset = min(TODAY.weekday(), 4)  # Up to Friday or current day if earlier

    for employee_id in [MANAGER_ID, CASHIER_ID]:
        # Monday to current day of current week
        for day_offset in range(current_day_offset + 1):
            work_day = MONDAY_OF_WEEK + timedelta(days=day_offset)

            # Morning shift
            clock_in = work_day.replace(hour=9, minute=0)

            # If it's today, don't clock out yet
            if day_offset == current_day_offset and NOW.hour < 17:
                # Only create active shift if during work hours
                if NOW.hour >= 9:
                    hour_data = {
                        "employee_id": employee_id,
                        "store_id": STORE_ID,
                        "clock_in": clock_in,
                        "status": "pending",
                        "notes": f"Current shift - {work_day.strftime('%A')}",
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }

                    # Insert directly
                    result = await hours_collection.insert_one(hour_data)
                    if result.inserted_id:
                        print(f"Created active hour record for {employee_id} on {work_day.date()}")
                        inserted_doc = await hours_collection.find_one({"_id": result.inserted_id})
                        hours_data.append(inserted_doc)
                    else:
                        print(f"Failed to create active hour record")
            else:
                # Complete shift for previous days
                clock_out = work_day.replace(hour=17, minute=30)

                # Break from 12-12:30
                break_start = work_day.replace(hour=12, minute=0)
                break_end = work_day.replace(hour=12, minute=30)

                # Calculate total minutes (excluding break)
                work_minutes = int((clock_out - clock_in).total_seconds() / 60)
                break_minutes = int((break_end - break_start).total_seconds() / 60)
                total_minutes = work_minutes - break_minutes

                hour_data = {
                    "employee_id": employee_id,
                    "store_id": STORE_ID,
                    "clock_in": clock_in,
                    "clock_out": clock_out,
                    "break_start": break_start,
                    "break_end": break_end,
                    "total_minutes": total_minutes,
                    "status": "pending",  # Pending approval for current week
                    "notes": f"Regular shift - {work_day.strftime('%A')}",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }

                # Insert directly
                result = await hours_collection.insert_one(hour_data)
                if result.inserted_id:
                    print(f"Created hour record for {employee_id} on {work_day.date()}")
                    inserted_doc = await hours_collection.find_one({"_id": result.inserted_id})
                    hours_data.append(inserted_doc)
                else:
                    print(f"Failed to create hour record")

    print(f"Created {len(hours_data)} hour records")
    return hours_data


async def generate_test_schedules():
    """Generate test schedules directly into the database"""
    schedules_collection = get_schedules_collection()
    schedules_data = []

    # Previous week schedule
    prev_week_shifts = []

    # Add shifts for manager
    for day_offset in range(5):  # Monday to Friday
        work_day = PREVIOUS_MONDAY + timedelta(days=day_offset)
        day_str = work_day.strftime("%Y-%m-%d")

        shift = {
            "_id": str(ObjectId()),
            "employee_id": MANAGER_ID,
            "date": day_str,
            "start_time": "09:00",
            "end_time": "17:30",
            "notes": f"Manager shift - {work_day.strftime('%A')}"
        }
        prev_week_shifts.append(shift)

    # Add shifts for cashier
    for day_offset in range(5):  # Monday to Friday
        work_day = PREVIOUS_MONDAY + timedelta(days=day_offset)
        day_str = work_day.strftime("%Y-%m-%d")

        shift = {
            "_id": str(ObjectId()),
            "employee_id": CASHIER_ID,
            "date": day_str,
            "start_time": "09:00",
            "end_time": "17:30",
            "notes": f"Cashier shift - {work_day.strftime('%A')}"
        }
        prev_week_shifts.append(shift)

    # Create previous week schedule document
    prev_week_schedule = {
        "title": f"Weekly Schedule: {PREVIOUS_MONDAY.date()} - {(PREVIOUS_MONDAY + timedelta(days=6)).date()}",
        "store_id": STORE_ID,
        "start_date": PREVIOUS_MONDAY.strftime("%Y-%m-%d"),
        "end_date": (PREVIOUS_MONDAY + timedelta(days=6)).strftime("%Y-%m-%d"),
        "shifts": prev_week_shifts,
        "created_by": MANAGER_USER_ID,
        "created_at": datetime.utcnow() - timedelta(days=10),
        "updated_at": datetime.utcnow() - timedelta(days=10)
    }

    # Insert directly
    result = await schedules_collection.insert_one(prev_week_schedule)
    if result.inserted_id:
        print(f"Created previous week schedule: {result.inserted_id}")
        prev_week_schedule["_id"] = result.inserted_id
        schedules_data.append(prev_week_schedule)
    else:
        print("Failed to create previous week schedule")

    # Current week schedule
    current_week_shifts = []

    # Add shifts for manager
    for day_offset in range(5):  # Monday to Friday
        work_day = MONDAY_OF_WEEK + timedelta(days=day_offset)
        day_str = work_day.strftime("%Y-%m-%d")

        shift = {
            "_id": str(ObjectId()),
            "employee_id": MANAGER_ID,
            "date": day_str,
            "start_time": "09:00",
            "end_time": "17:30",
            "notes": f"Manager shift - {work_day.strftime('%A')}"
        }
        current_week_shifts.append(shift)

    # Add shifts for cashier
    for day_offset in range(5):  # Monday to Friday
        work_day = MONDAY_OF_WEEK + timedelta(days=day_offset)
        day_str = work_day.strftime("%Y-%m-%d")

        shift = {
            "_id": str(ObjectId()),
            "employee_id": CASHIER_ID,
            "date": day_str,
            "start_time": "09:00",
            "end_time": "17:30",
            "notes": f"Cashier shift - {work_day.strftime('%A')}"
        }
        current_week_shifts.append(shift)

    # Create current week schedule document
    current_week_schedule = {
        "title": f"Weekly Schedule: {MONDAY_OF_WEEK.date()} - {(MONDAY_OF_WEEK + timedelta(days=6)).date()}",
        "store_id": STORE_ID,
        "start_date": MONDAY_OF_WEEK.strftime("%Y-%m-%d"),
        "end_date": (MONDAY_OF_WEEK + timedelta(days=6)).strftime("%Y-%m-%d"),
        "shifts": current_week_shifts,
        "created_by": MANAGER_USER_ID,
        "created_at": datetime.utcnow() - timedelta(days=3),
        "updated_at": datetime.utcnow() - timedelta(days=3)
    }

    # Insert directly
    result = await schedules_collection.insert_one(current_week_schedule)
    if result.inserted_id:
        print(f"Created current week schedule: {result.inserted_id}")
        current_week_schedule["_id"] = result.inserted_id
        schedules_data.append(current_week_schedule)
    else:
        print("Failed to create current week schedule")

    return schedules_data


async def generate_simple_timesheets():
    """Generate timesheets directly into the database"""
    timesheets_collection = get_timesheets_collection()

    # Get all hour records we just created
    hours_collection = get_hours_collection()
    prev_week_hours_mgr = await hours_collection.find({
        "employee_id": MANAGER_ID,
        "clock_in": {
            "$gte": PREVIOUS_MONDAY,
            "$lt": MONDAY_OF_WEEK
        }
    }).to_list(length=100)

    prev_week_hours_cashier = await hours_collection.find({
        "employee_id": CASHIER_ID,
        "clock_in": {
            "$gte": PREVIOUS_MONDAY,
            "$lt": MONDAY_OF_WEEK
        }
    }).to_list(length=100)

    current_week_hours_mgr = await hours_collection.find({
        "employee_id": MANAGER_ID,
        "clock_in": {
            "$gte": MONDAY_OF_WEEK
        }
    }).to_list(length=100)

    current_week_hours_cashier = await hours_collection.find({
        "employee_id": CASHIER_ID,
        "clock_in": {
            "$gte": MONDAY_OF_WEEK
        }
    }).to_list(length=100)

    timesheets = []

    # Previous week - Manager (approved)
    if prev_week_hours_mgr:
        # Calculate total hours
        total_hours = sum(h.get("total_minutes", 0) for h in prev_week_hours_mgr) / 60

        mgr_timesheet = {
            "employee_id": MANAGER_ID,
            "store_id": STORE_ID,
            "week_start_date": PREVIOUS_MONDAY.strftime("%Y-%m-%d"),
            "week_end_date": (PREVIOUS_MONDAY + timedelta(days=6)).strftime("%Y-%m-%d"),
            "time_entries": [str(h["_id"]) for h in prev_week_hours_mgr],
            "total_hours": total_hours,
            "status": "approved",
            "submitted_at": datetime.utcnow() - timedelta(days=3),
            "approved_by": MANAGER_USER_ID,
            "approved_at": datetime.utcnow() - timedelta(days=2),
            "notes": "Regular work week",
            "created_at": datetime.utcnow() - timedelta(days=4),
            "updated_at": datetime.utcnow() - timedelta(days=2)
        }

        result = await timesheets_collection.insert_one(mgr_timesheet)
        if result.inserted_id:
            print(f"Created approved timesheet for manager (previous week): {result.inserted_id}")
            mgr_timesheet["_id"] = result.inserted_id
            timesheets.append(mgr_timesheet)

    # Previous week - Cashier (rejected)
    if prev_week_hours_cashier:
        # Calculate total hours
        total_hours = sum(h.get("total_minutes", 0) for h in prev_week_hours_cashier) / 60

        cashier_timesheet = {
            "employee_id": CASHIER_ID,
            "store_id": STORE_ID,
            "week_start_date": PREVIOUS_MONDAY.strftime("%Y-%m-%d"),
            "week_end_date": (PREVIOUS_MONDAY + timedelta(days=6)).strftime("%Y-%m-%d"),
            "time_entries": [str(h["_id"]) for h in prev_week_hours_cashier],
            "total_hours": total_hours,
            "status": "rejected",
            "submitted_at": datetime.utcnow() - timedelta(days=3),
            "approved_by": MANAGER_USER_ID,
            "approved_at": datetime.utcnow() - timedelta(days=2),
            "notes": "Regular work week",
            "rejection_reason": "Missing lunch break on Wednesday",
            "created_at": datetime.utcnow() - timedelta(days=4),
            "updated_at": datetime.utcnow() - timedelta(days=2)
        }

        result = await timesheets_collection.insert_one(cashier_timesheet)
        if result.inserted_id:
            print(f"Created rejected timesheet for cashier (previous week): {result.inserted_id}")
            cashier_timesheet["_id"] = result.inserted_id
            timesheets.append(cashier_timesheet)

    # Current week - Manager (draft)
    if current_week_hours_mgr:
        # Calculate total hours
        total_hours = sum(h.get("total_minutes", 0) for h in current_week_hours_mgr) / 60

        mgr_current_timesheet = {
            "employee_id": MANAGER_ID,
            "store_id": STORE_ID,
            "week_start_date": MONDAY_OF_WEEK.strftime("%Y-%m-%d"),
            "week_end_date": (MONDAY_OF_WEEK + timedelta(days=6)).strftime("%Y-%m-%d"),
            "time_entries": [str(h["_id"]) for h in current_week_hours_mgr],
            "total_hours": total_hours,
            "status": "draft",
            "notes": "Current week in progress",
            "created_at": datetime.utcnow() - timedelta(days=1),
            "updated_at": datetime.utcnow() - timedelta(days=1)
        }

        result = await timesheets_collection.insert_one(mgr_current_timesheet)
        if result.inserted_id:
            print(f"Created draft timesheet for manager (current week): {result.inserted_id}")
            mgr_current_timesheet["_id"] = result.inserted_id
            timesheets.append(mgr_current_timesheet)

    # Current week - Cashier (submitted if Thursday or later)
    if current_week_hours_cashier:
        # Calculate total hours
        total_hours = sum(h.get("total_minutes", 0) for h in current_week_hours_cashier) / 60

        cashier_current_timesheet = {
            "employee_id": CASHIER_ID,
            "store_id": STORE_ID,
            "week_start_date": MONDAY_OF_WEEK.strftime("%Y-%m-%d"),
            "week_end_date": (MONDAY_OF_WEEK + timedelta(days=6)).strftime("%Y-%m-%d"),
            "time_entries": [str(h["_id"]) for h in current_week_hours_cashier],
            "total_hours": total_hours,
            "status": "submitted" if TODAY.weekday() >= 3 else "draft",
            "submitted_at": datetime.utcnow() if TODAY.weekday() >= 3 else None,
            "notes": "Submitting timesheet for current week" if TODAY.weekday() >= 3 else "Current week in progress",
            "created_at": datetime.utcnow() - timedelta(days=1),
            "updated_at": datetime.utcnow() if TODAY.weekday() >= 3 else datetime.utcnow() - timedelta(days=1)
        }

        result = await timesheets_collection.insert_one(cashier_current_timesheet)
        if result.inserted_id:
            status = "submitted" if TODAY.weekday() >= 3 else "draft"
            print(f"Created {status} timesheet for cashier (current week): {result.inserted_id}")
            cashier_current_timesheet["_id"] = result.inserted_id
            timesheets.append(cashier_current_timesheet)

    return timesheets


async def main():
    """Main function to generate test data"""
    try:
        print("Starting complete test data generation...")

        # Generate hours records
        hours_data = await generate_test_hours()

        # Generate schedules
        schedules_data = await generate_test_schedules()

        # Generate timesheets from those hours
        timesheets_data = await generate_simple_timesheets()

        print("Test data generation complete!")

        # Print summary
        print("\nSummary:")
        print(f"  - Hours records created: {len(hours_data)}")
        print(f"  - Schedules created: {len(schedules_data)}")
        print(f"  - Timesheets created: {len(timesheets_data)}")

    except Exception as e:
        print(f"Error generating test data: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())