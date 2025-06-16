from fasthtml.common import *
from monsterui.all import *
from starmodel import *
from pages.templates import app_template
import random
from datetime import datetime

rt = APIRouter()


class TaskManager(Entity):
    model_config = {
        "namespace": "TaskManager",  # Custom namespace (default: class name)
        "use_namespace": True,       # Use namespaced signals: $TaskManager.field
        "store": EntityStore.SERVER_MEMORY,  # Storage backend
        "auto_persist": True,        # Auto-save after each event
        "sync_with_client": True,    # Auto-sync with client signals
    }
    
    tasks: List[Dict] = []
    filter_status: str = "all"
    new_task_text: str = ""
    is_loading: bool = False
    
    @event
    def add_task(self, new_task_text: str):
        """Add a new task - auto-creates endpoint /TaskManager/add_task"""
        if new_task_text.strip():
            task = {
                "id": len(self.tasks) + 1,
                "text": new_task_text.strip(),
                "completed": False,
                "created_at": datetime.now().isoformat()
            }
            self.tasks.append(task)
            self.new_task_text = ""  # Clear input
            
            # Return HTML fragment to update UI
            return Div(id="task-list")(
                *[self.task_item(t) for t in self.filtered_tasks()]
            )
        
    @event
    def delete_task(self, task_id: int):
        """Delete a task"""
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        
        # Return HTML fragment to update UI
        return Div(id="task-list")(
            *[self.task_item(t) for t in self.filtered_tasks()]
        )
    
    @event(method="patch")
    def toggle_task(self, task_id: int):
        """Toggle task completion status"""
        for task in self.tasks:
            if task["id"] == task_id:
                task["completed"] = not task["completed"]
                break
        
        # Return updated task item
        return self.task_item(next(t for t in self.tasks if t["id"] == task_id))
    
    def filtered_tasks(self):
        """Computed property for filtered tasks"""
        if self.filter_status == "active":
            return [t for t in self.tasks if not t["completed"]]
        elif self.filter_status == "completed":
            return [t for t in self.tasks if t["completed"]]
        return self.tasks
    
    def task_item(self, task):
        """Reusable task component"""
        return Div(cls="task-item", id=f"task-{task['id']}")(
            CheckboxX(
                {f"data-on-click": TaskManager.toggle_task(task["id"])},
                checked=task["completed"],
            ),
            Span(
                task["text"],
                cls="completed" if task["completed"] else ""
            ),
            Button(
                UkIcon("trash"),
                {f"data-on-click": TaskManager.delete_task(task["id"])},
                cls=ButtonT.icon
            )
        )

# Usage in FastHTML route
@rt("/tasks")
@app_template(title="Tasks")
def index(req: Request):
    task_manager = TaskManager.get(req)  # Get or create instance
    
    return Main(
        task_manager,  # Auto-renders signals div with persistence
        H1("Task Manager"),
        
        # Add task form
        Form({f"data-on-submit": TaskManager.add_task()})(
            Input(
                {f"data-bind": TaskManager.new_task_text_signal},
                placeholder="New task...",
                name="text"
            ),
            Button("Add Task", type="submit")
        ),
        
        # Task list
        Div(id="task-list")(
            *[task_manager.task_item(t) for t in task_manager.filtered_tasks()]
        )
    )
