"""
Interview Scheduler for RUME AI.
Manages interview scheduling, calendar integration, and automated reminders.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class InterviewSlot:
    """Represents an available interview slot."""
    id: str
    start_time: datetime
    end_time: datetime
    interviewer_id: str
    interviewer_name: str
    status: str = "available"  # available, booked, cancelled
    candidate_id: Optional[str] = None
    job_id: Optional[str] = None
    interview_type: str = "screening"  # screening, technical, behavioral, final
    notes: Optional[str] = None

@dataclass
class InterviewRequest:
    """Request model for scheduling an interview."""
    candidate_id: str
    job_id: str
    interviewer_id: str
    preferred_slots: List[datetime]
    interview_type: str = "screening"
    duration_minutes: int = 60
    notes: Optional[str] = None

@dataclass
class InterviewReminder:
    """Represents an interview reminder."""
    interview_id: str
    reminder_time: datetime
    recipient_type: str  # candidate, interviewer, both
    sent: bool = False
    method: str = "email"  # email, sms, both

class InterviewScheduler:
    """Manages interview scheduling and calendar operations."""
    
    def __init__(self):
        self.slots: Dict[str, InterviewSlot] = {}
        self.reminders: Dict[str, InterviewReminder] = {}
        self.interview_history: List[Dict[str, Any]] = []
        
        # Default interview durations by type
        self.default_durations = {
            "screening": 30,
            "technical": 60,
            "behavioral": 45,
            "final": 90
        }
    
    def create_interview_slot(
        self,
        start_time: datetime,
        end_time: datetime,
        interviewer_id: str,
        interviewer_name: str,
        interview_type: str = "screening"
    ) -> InterviewSlot:
        """
        Create a new available interview slot.
        
        Args:
            start_time: Start time of the slot
            end_time: End time of the slot
            interviewer_id: ID of the interviewer
            interviewer_name: Name of the interviewer
            interview_type: Type of interview
        
        Returns:
            Created InterviewSlot
        """
        slot_id = f"slot_{int(datetime.now().timestamp())}_{len(self.slots)}"
        
        slot = InterviewSlot(
            id=slot_id,
            start_time=start_time,
            end_time=end_time,
            interviewer_id=interviewer_id,
            interviewer_name=interviewer_name,
            interview_type=interview_type
        )
        
        self.slots[slot_id] = slot
        logger.info(f"Created interview slot {slot_id} for {interviewer_name}")
        
        return slot
    
    def get_available_slots(
        self,
        interviewer_id: Optional[str] = None,
        interview_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[InterviewSlot]:
        """
        Get available interview slots with optional filtering.
        
        Args:
            interviewer_id: Filter by interviewer
            interview_type: Filter by interview type
            start_date: Filter slots after this date
            end_date: Filter slots before this date
        
        Returns:
            List of available InterviewSlot objects
        """
        available_slots = []
        
        for slot in self.slots.values():
            if slot.status != "available":
                continue
            
            if interviewer_id and slot.interviewer_id != interviewer_id:
                continue
            
            if interview_type and slot.interview_type != interview_type:
                continue
            
            if start_date and slot.start_time < start_date:
                continue
            
            if end_date and slot.end_time > end_date:
                continue
            
            available_slots.append(slot)
        
        # Sort by start time
        available_slots.sort(key=lambda x: x.start_time)
        
        return available_slots
    
    def schedule_interview(
        self,
        request: InterviewRequest
    ) -> Optional[InterviewSlot]:
        """
        Schedule an interview based on request and available slots.
        
        Args:
            request: InterviewRequest with scheduling details
        
        Returns:
            Scheduled InterviewSlot or None if no suitable slot found
        """
        # Find best matching slot
        best_slot = None
        best_score = -1
        
        for slot in self.get_available_slots(
            interviewer_id=request.interviewer_id,
            interview_type=request.interview_type
        ):
            # Score based on preference match
            score = 0
            for preferred_time in request.preferred_slots:
                time_diff = abs((slot.start_time - preferred_time).total_seconds())
                if time_diff < 3600:  # Within 1 hour
                    score += 10
                elif time_diff < 7200:  # Within 2 hours
                    score += 5
                elif time_diff < 86400:  # Within 1 day
                    score += 2
            
            if score > best_score:
                best_score = score
                best_slot = slot
        
        if not best_slot:
            logger.warning(f"No suitable slot found for interview request")
            return None
        
        # Book the slot
        best_slot.status = "booked"
        best_slot.candidate_id = request.candidate_id
        best_slot.job_id = request.job_id
        best_slot.notes = request.notes
        
        # Create reminders
        self._create_reminders(best_slot)
        
        # Add to history
        self.interview_history.append({
            "slot_id": best_slot.id,
            "candidate_id": request.candidate_id,
            "job_id": request.job_id,
            "scheduled_at": datetime.now(),
            "interview_time": best_slot.start_time
        })
        
        logger.info(f"Scheduled interview {best_slot.id} for candidate {request.candidate_id}")
        
        return best_slot
    
    def cancel_interview(self, slot_id: str) -> bool:
        """
        Cancel a scheduled interview.
        
        Args:
            slot_id: ID of the interview slot to cancel
        
        Returns:
            True if cancelled successfully, False otherwise
        """
        if slot_id not in self.slots:
            logger.warning(f"Slot {slot_id} not found")
            return False
        
        slot = self.slots[slot_id]
        
        if slot.status != "booked":
            logger.warning(f"Slot {slot_id} is not booked")
            return False
        
        slot.status = "cancelled"
        slot.candidate_id = None
        slot.job_id = None
        
        # Remove associated reminders
        self.reminders = {
            k: v for k, v in self.reminders.items()
            if v.interview_id != slot_id
        }
        
        logger.info(f"Cancelled interview {slot_id}")
        
        return True
    
    def reschedule_interview(
        self,
        slot_id: str,
        new_start_time: datetime,
        new_end_time: datetime
    ) -> bool:
        """
        Reschedule an interview to a new time.
        
        Args:
            slot_id: ID of the interview to reschedule
            new_start_time: New start time
            new_end_time: New end time
        
        Returns:
            True if rescheduled successfully, False otherwise
        """
        if slot_id not in self.slots:
            logger.warning(f"Slot {slot_id} not found")
            return False
        
        slot = self.slots[slot_id]
        
        if slot.status != "booked":
            logger.warning(f"Slot {slot_id} is not booked")
            return False
        
        # Update times
        slot.start_time = new_start_time
        slot.end_time = new_end_time
        
        # Recreate reminders with new times
        self.reminders = {
            k: v for k, v in self.reminders.items()
            if v.interview_id != slot_id
        }
        self._create_reminders(slot)
        
        logger.info(f"Rescheduled interview {slot_id} to {new_start_time}")
        
        return True
    
    def _create_reminders(self, slot: InterviewSlot):
        """Create automatic reminders for an interview."""
        reminder_times = [
            slot.start_time - timedelta(days=1),  # 1 day before
            slot.start_time - timedelta(hours=2),  # 2 hours before
            slot.start_time - timedelta(minutes=15),  # 15 minutes before
        ]
        
        for i, reminder_time in enumerate(reminder_times):
            reminder_id = f"reminder_{slot.id}_{i}"
            
            reminder = InterviewReminder(
                interview_id=slot.id,
                reminder_time=reminder_time,
                recipient_type="both",
                sent=False,
                method="email"
            )
            
            self.reminders[reminder_id] = reminder
    
    def get_upcoming_interviews(
        self,
        interviewer_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        days_ahead: int = 7
    ) -> List[InterviewSlot]:
        """
        Get upcoming scheduled interviews.
        
        Args:
            interviewer_id: Filter by interviewer
            candidate_id: Filter by candidate
            days_ahead: Number of days ahead to look
        
        Returns:
            List of upcoming InterviewSlot objects
        """
        cutoff_date = datetime.now() + timedelta(days=days_ahead)
        upcoming = []
        
        for slot in self.slots.values():
            if slot.status != "booked":
                continue
            
            if slot.start_time < datetime.now():
                continue
            
            if slot.start_time > cutoff_date:
                continue
            
            if interviewer_id and slot.interviewer_id != interviewer_id:
                continue
            
            if candidate_id and slot.candidate_id != candidate_id:
                continue
            
            upcoming.append(slot)
        
        upcoming.sort(key=lambda x: x.start_time)
        
        return upcoming
    
    def get_interview_statistics(self) -> Dict[str, Any]:
        """
        Get interview scheduling statistics.
        
        Returns:
            Dictionary with scheduling statistics
        """
        total_slots = len(self.slots)
        booked_slots = sum(1 for s in self.slots.values() if s.status == "booked")
        available_slots = sum(1 for s in self.slots.values() if s.status == "available")
        cancelled_slots = sum(1 for s in self.slots.values() if s.status == "cancelled")
        
        # Interviews by type
        by_type = {}
        for slot in self.slots.values():
            if slot.status == "booked":
                by_type[slot.interview_type] = by_type.get(slot.interview_type, 0) + 1
        
        # Interviews by interviewer
        by_interviewer = {}
        for slot in self.slots.values():
            if slot.status == "booked":
                by_interviewer[slot.interviewer_name] = by_interviewer.get(slot.interviewer_name, 0) + 1
        
        return {
            "total_slots": total_slots,
            "booked_slots": booked_slots,
            "available_slots": available_slots,
            "cancelled_slots": cancelled_slots,
            "booking_rate": booked_slots / total_slots if total_slots > 0 else 0,
            "by_type": by_type,
            "by_interviewer": by_interviewer,
            "total_interviews_conducted": len(self.interview_history)
        }
    
    def export_schedule(self, format: str = "json") -> str:
        """
        Export interview schedule in specified format.
        
        Args:
            format: Export format (json, csv)
        
        Returns:
            Exported schedule as string
        """
        if format == "json":
            schedule_data = {
                "slots": [
                    {
                        "id": slot.id,
                        "start_time": slot.start_time.isoformat(),
                        "end_time": slot.end_time.isoformat(),
                        "interviewer": slot.interviewer_name,
                        "status": slot.status,
                        "candidate_id": slot.candidate_id,
                        "job_id": slot.job_id,
                        "type": slot.interview_type,
                        "notes": slot.notes
                    }
                    for slot in self.slots.values()
                ],
                "statistics": self.get_interview_statistics()
            }
            return json.dumps(schedule_data, indent=2)
        
        elif format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            writer.writerow([
                "ID", "Start Time", "End Time", "Interviewer", 
                "Status", "Candidate ID", "Job ID", "Type", "Notes"
            ])
            
            for slot in self.slots.values():
                writer.writerow([
                    slot.id,
                    slot.start_time.isoformat(),
                    slot.end_time.isoformat(),
                    slot.interviewer_name,
                    slot.status,
                    slot.candidate_id or "",
                    slot.job_id or "",
                    slot.interview_type,
                    slot.notes or ""
                ])
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported format: {format}")

# Global interview scheduler instance
interview_scheduler = InterviewScheduler()

def test_interview_scheduler():
    """Test the interview scheduler functionality."""
    scheduler = InterviewScheduler()
    
    # Create some test slots
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    
    slot1 = scheduler.create_interview_slot(
        start_time=tomorrow.replace(hour=10, minute=0),
        end_time=tomorrow.replace(hour=11, minute=0),
        interviewer_id="int1",
        interviewer_name="John Smith",
        interview_type="screening"
    )
    
    slot2 = scheduler.create_interview_slot(
        start_time=tomorrow.replace(hour=14, minute=0),
        end_time=tomorrow.replace(hour=15, minute=0),
        interviewer_id="int1",
        interviewer_name="John Smith",
        interview_type="technical"
    )
    
    # Schedule an interview
    request = InterviewRequest(
        candidate_id="cand1",
        job_id="job1",
        interviewer_id="int1",
        preferred_slots=[tomorrow.replace(hour=10, minute=30)],
        interview_type="screening"
    )
    
    scheduled = scheduler.schedule_interview(request)
    
    print(f"Scheduled interview: {scheduled.id if scheduled else 'None'}")
    print(f"Statistics: {scheduler.get_interview_statistics()}")
    
    # Get upcoming interviews
    upcoming = scheduler.get_upcoming_interviews(days_ahead=2)
    print(f"Upcoming interviews: {len(upcoming)}")

if __name__ == "__main__":
    test_interview_scheduler()
