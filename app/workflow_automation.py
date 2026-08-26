"""
Workflow Automation for RUME AI.
Automates hiring workflows with customizable triggers and actions.
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class TriggerType(Enum):
    """Types of workflow triggers."""
    CANDIDATE_APPLIED = "candidate_applied"
    CANDIDATE_HIRED = "candidate_hired"
    CANDIDATE_REJECTED = "candidate_rejected"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_COMPLETED = "interview_completed"
    SCORE_THRESHOLD = "score_threshold"
    TIME_ELAPSED = "time_elapsed"
    MANUAL = "manual"

class ActionType(Enum):
    """Types of workflow actions."""
    SEND_EMAIL = "send_email"
    UPDATE_STATUS = "update_status"
    ASSIGN_INTERVIEWER = "assign_interviewer"
    CREATE_TASK = "create_task"
    SEND_NOTIFICATION = "send_notification"
    ADD_TAG = "add_tag"
    MOVE_STAGE = "move_stage"
    WEBHOOK_CALL = "webhook_call"

@dataclass
class WorkflowTrigger:
    """Represents a workflow trigger."""
    trigger_type: TriggerType
    conditions: Dict[str, Any]
    enabled: bool = True

@dataclass
class WorkflowAction:
    """Represents a workflow action."""
    action_type: ActionType
    parameters: Dict[str, Any]
    delay_seconds: int = 0

@dataclass
class Workflow:
    """Represents an automated workflow."""
    workflow_id: str
    name: str
    description: str
    trigger: WorkflowTrigger
    actions: List[WorkflowAction]
    enabled: bool = True
    created_at: datetime = None
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

@dataclass
class WorkflowExecution:
    """Represents a workflow execution."""
    execution_id: str
    workflow_id: str
    triggered_at: datetime
    status: str  # running, completed, failed
    results: List[Dict[str, Any]]
    error_message: Optional[str] = None

class WorkflowAutomationService:
    """Service for automating hiring workflows."""
    
    def __init__(self):
        self.workflows: Dict[str, Workflow] = {}
        self.execution_history: List[WorkflowExecution] = []
        self.workflow_counter = 0
        self.execution_counter = 0
        
        # Action handlers
        self.action_handlers = {
            ActionType.SEND_EMAIL: self._handle_send_email,
            ActionType.UPDATE_STATUS: self._handle_update_status,
            ActionType.ASSIGN_INTERVIEWER: self._handle_assign_interviewer,
            ActionType.CREATE_TASK: self._handle_create_task,
            ActionType.SEND_NOTIFICATION: self._handle_send_notification,
            ActionType.ADD_TAG: self._handle_add_tag,
            ActionType.MOVE_STAGE: self._handle_move_stage,
            ActionType.WEBHOOK_CALL: self._handle_webhook_call
        }
    
    def create_workflow(
        self,
        name: str,
        description: str,
        trigger: WorkflowTrigger,
        actions: List[WorkflowAction]
    ) -> Workflow:
        """
        Create a new workflow.
        
        Args:
            name: Workflow name
            description: Workflow description
            trigger: Trigger configuration
            actions: List of actions to execute
        
        Returns:
            Created Workflow object
        """
        self.workflow_counter += 1
        workflow_id = f"wf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.workflow_counter}"
        
        workflow = Workflow(
            workflow_id=workflow_id,
            name=name,
            description=description,
            trigger=trigger,
            actions=actions,
            enabled=True,
            created_at=datetime.now()
        )
        
        self.workflows[workflow_id] = workflow
        logger.info(f"Created workflow {workflow_id}: {name}")
        
        return workflow
    
    def trigger_workflow(
        self,
        event_type: TriggerType,
        event_data: Dict[str, Any]
    ) -> List[WorkflowExecution]:
        """
        Trigger workflows based on an event.
        
        Args:
            event_type: Type of event that occurred
            event_data: Data associated with the event
        
        Returns:
            List of WorkflowExecution objects
        """
        executions = []
        
        for workflow in self.workflows.values():
            if not workflow.enabled:
                continue
            
            if not self._should_trigger(workflow, event_type, event_data):
                continue
            
            execution = self._execute_workflow(workflow, event_data)
            executions.append(execution)
        
        return executions
    
    def _should_trigger(
        self,
        workflow: Workflow,
        event_type: TriggerType,
        event_data: Dict[str, Any]
    ) -> bool:
        """Check if workflow should be triggered."""
        if workflow.trigger.trigger_type != event_type:
            return False
        
        # Check trigger conditions
        conditions = workflow.trigger.conditions
        
        # Score threshold check
        if 'min_score' in conditions:
            if event_data.get('score', 0) < conditions['min_score']:
                return False
        
        # Status check
        if 'required_status' in conditions:
            if event_data.get('status') != conditions['required_status']:
                return False
        
        # Time elapsed check
        if 'min_hours_elapsed' in conditions:
            applied_date = event_data.get('applied_date')
            if applied_date:
                elapsed = (datetime.now() - applied_date).total_seconds() / 3600
                if elapsed < conditions['min_hours_elapsed']:
                    return False
        
        return True
    
    def _execute_workflow(
        self,
        workflow: Workflow,
        event_data: Dict[str, Any]
    ) -> WorkflowExecution:
        """Execute a workflow."""
        self.execution_counter += 1
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.execution_counter}"
        
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow.workflow_id,
            triggered_at=datetime.now(),
            status="running",
            results=[]
        )
        
        # Update workflow stats
        workflow.last_triggered = datetime.now()
        workflow.trigger_count += 1
        
        try:
            # Execute actions in sequence
            for action in workflow.actions:
                # Apply delay if specified
                if action.delay_seconds > 0:
                    import time
                    time.sleep(action.delay_seconds)
                
                # Execute action
                result = self._execute_action(action, event_data)
                execution.results.append(result)
            
            execution.status = "completed"
            logger.info(f"Workflow {workflow.workflow_id} executed successfully")
            
        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            logger.error(f"Workflow {workflow.workflow_id} failed: {e}")
        
        self.execution_history.append(execution)
        
        return execution
    
    def _execute_action(
        self,
        action: WorkflowAction,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single action."""
        handler = self.action_handlers.get(action.action_type)
        
        if not handler:
            logger.warning(f"No handler for action type: {action.action_type}")
            return {'success': False, 'error': 'No handler found'}
        
        return handler(action.parameters, event_data)
    
    def _handle_send_email(
        self,
        parameters: Dict[str, Any],
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle send email action."""
        # In production, this would use the email notification service
        logger.info(f"Sending email to {parameters.get('to')}")
        return {'success': True, 'action': 'send_email'}
    
    def _handle_update_status(
        self,
        parameters: Dict[str, Any],
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle update status action."""
        new_status = parameters.get('status')
        candidate_id = event_data.get('candidate_id')
        
        logger.info(f"Updating candidate {candidate_id} status to {new_status}")
        return {'success': True, 'action': 'update_status', 'new_status': new_status}
    
    def _handle_assign_interviewer(
        self,
        parameters: Dict[str, Any],
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle assign interviewer action."""
        interviewer_id = parameters.get('interviewer_id')
        candidate_id = event_data.get('candidate_id')
        
        logger.info(f"Assigning interviewer {interviewer_id} to candidate {candidate_id}")
        return {'success': True, 'action': 'assign_interviewer'}
    
    def _handle_create_task(
        self,
        parameters: Dict[str, Any],
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle create task action."""
        task_title = parameters.get('title')
        assignee = parameters.get('assignee')
        
        logger.info(f"Creating task '{task_title}' assigned to {assignee}")
        return {'success': True, 'action': 'create_task'}
    
    def _handle_send_notification(
        self,
        parameters: Dict[str, Any],
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle send notification action."""
        message = parameters.get('message')
        recipient = parameters.get('recipient')
        
        logger.info(f"Sending notification to {recipient}: {message}")
        return {'success': True, 'action': 'send_notification'}
    
    def _handle_add_tag(
        self,
        parameters: Dict[str, Any],
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle add tag action."""
        tag = parameters.get('tag')
        candidate_id = event_data.get('candidate_id')
        
        logger.info(f"Adding tag '{tag}' to candidate {candidate_id}")
        return {'success': True, 'action': 'add_tag', 'tag': tag}
    
    def _handle_move_stage(
        self,
        parameters: Dict[str, Any],
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle move stage action."""
        new_stage = parameters.get('stage')
        candidate_id = event_data.get('candidate_id')
        
        logger.info(f"Moving candidate {candidate_id} to stage {new_stage}")
        return {'success': True, 'action': 'move_stage', 'new_stage': new_stage}
    
    def _handle_webhook_call(
        self,
        parameters: Dict[str, Any],
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle webhook call action."""
        url = parameters.get('url')
        method = parameters.get('method', 'POST')
        
        logger.info(f"Calling webhook {url} with method {method}")
        # In production, this would make an actual HTTP request
        return {'success': True, 'action': 'webhook_call', 'url': url}
    
    def enable_workflow(self, workflow_id: str) -> bool:
        """Enable a workflow."""
        if workflow_id in self.workflows:
            self.workflows[workflow_id].enabled = True
            logger.info(f"Enabled workflow {workflow_id}")
            return True
        return False
    
    def disable_workflow(self, workflow_id: str) -> bool:
        """Disable a workflow."""
        if workflow_id in self.workflows:
            self.workflows[workflow_id].enabled = False
            logger.info(f"Disabled workflow {workflow_id}")
            return True
        return False
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        if workflow_id in self.workflows:
            del self.workflows[workflow_id]
            logger.info(f"Deleted workflow {workflow_id}")
            return True
        return False
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID."""
        return self.workflows.get(workflow_id)
    
    def list_workflows(self, enabled_only: bool = False) -> List[Workflow]:
        """List all workflows."""
        workflows = list(self.workflows.values())
        
        if enabled_only:
            workflows = [w for w in workflows if w.enabled]
        
        return workflows
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """Get workflow statistics."""
        total_workflows = len(self.workflows)
        enabled_workflows = sum(1 for w in self.workflows.values() if w.enabled)
        total_executions = len(self.execution_history)
        successful_executions = sum(1 for e in self.execution_history if e.status == "completed")
        
        # Most triggered workflows
        trigger_counts = {}
        for workflow in self.workflows.values():
            trigger_counts[workflow.name] = workflow.trigger_count
        
        top_workflows = sorted(
            trigger_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            'total_workflows': total_workflows,
            'enabled_workflows': enabled_workflows,
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'success_rate': successful_executions / total_executions if total_executions > 0 else 0,
            'top_triggered_workflows': top_workflows
        }
    
    def get_execution_history(
        self,
        workflow_id: Optional[str] = None,
        limit: int = 50
    ) -> List[WorkflowExecution]:
        """Get workflow execution history."""
        filtered = self.execution_history
        
        if workflow_id:
            filtered = [e for e in filtered if e.workflow_id == workflow_id]
        
        # Sort by triggered time descending
        filtered.sort(key=lambda x: x.triggered_at, reverse=True)
        
        return filtered[:limit]

# Global workflow automation service instance
workflow_automation_service = WorkflowAutomationService()

def test_workflow_automation():
    """Test the workflow automation service."""
    service = WorkflowAutomationService()
    
    # Create a simple workflow
    trigger = WorkflowTrigger(
        trigger_type=TriggerType.CANDIDATE_APPLIED,
        conditions={'min_score': 80}
    )
    
    actions = [
        WorkflowAction(
            action_type=ActionType.SEND_EMAIL,
            parameters={'template': 'application_received', 'to': 'candidate'}
        ),
        WorkflowAction(
            action_type=ActionType.ADD_TAG,
            parameters={'tag': 'high_potential'}
        )
    ]
    
    workflow = service.create_workflow(
        name="High Score Candidate Workflow",
        description="Automated actions for high-scoring candidates",
        trigger=trigger,
        actions=actions
    )
    
    print(f"Created workflow: {workflow.workflow_id}")
    
    # Trigger the workflow
    event_data = {
        'candidate_id': 'cand123',
        'score': 85,
        'status': 'applied',
        'applied_date': datetime.now()
    }
    
    executions = service.trigger_workflow(TriggerType.CANDIDATE_APPLIED, event_data)
    print(f"Triggered {len(executions)} executions")
    
    # Get statistics
    stats = service.get_workflow_statistics()
    print(f"Workflow statistics: {stats}")

if __name__ == "__main__":
    test_workflow_automation()
