# StarModel Development Guide: Reactive Entity Management with Datastar Attributes

**Entity-Centric Reactive Development for FastHTML with Comprehensive Datastar Integration**

StarModel revolutionizes web development by unifying data models and behavior in single Python classes. This guide provides complete coverage of all Datastar attributes with StarModel integration, focusing on precise implementation patterns for AI developer agents.

## Table of Contents

1. [Quick Setup & Core Concepts](#quick-setup--core-concepts)
2. [StarModel Fundamentals](#starmodel-fundamentals)
3. [Complete Datastar Attributes Reference](#complete-datastar-attributes-reference)
4. [Event Handling & Server-Side Integration](#event-handling--server-side-integration)
5. [Advanced Entity Management Patterns](#advanced-entity-management-patterns)
6. [Production-Ready Examples](#production-ready-examples)

## Quick Setup & Core Concepts

### Installation and Basic Setup

```python
# Install StarModel
pip install git+https://github.com/ndendic/StarModel.git

# Basic FastHTML + StarModel setup
from fasthtml.common import *
from starmodel import *

app, rt = fast_app(
    htmx=False,  # Disable HTMX, use Datastar instead
    hdrs=(datastar_script,)  # Include Datastar CDN script
)

# Add StarModel routes to FastHTML app
entities_rt.to_app(app)  # Essential: registers all @event routes
```

### Core StarModel Philosophy

**Entity-Centric Development**: Your `User`, `Product`, `Todo` entities contain both data schema AND business logic. No separation between models and controllers.

```python
class User(Entity):
    name: str = ""
    email: str = ""
    is_active: bool = True
    login_count: int = 0
    
    @event  # Automatically creates /User/login endpoint
    def login(self):
        self.login_count += 1
        self.is_active = True
        # Auto-persisted and signals updated automatically
    
    @event(method="post")  # Custom HTTP method
    def update_profile(self, name: str, email: str):
        self.name = name
        self.email = email
        return Div("Profile updated!")  # Return HTML fragments
```

## StarModel Fundamentals

### Entity Class Architecture

```python
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
    def add_task(self, text: str):
        """Add a new task - auto-creates endpoint /TaskManager/add_task"""
        if text.strip():
            task = {
                "id": len(self.tasks) + 1,
                "text": text.strip(),
                "completed": False,
                "created_at": datetime.now().isoformat()
            }
            self.tasks.append(task)
            self.new_task_text = ""  # Clear input
            
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
            Input(
                type="checkbox",
                checked=task["completed"],
                {f"data-on-click": TaskManager.toggle_task(task["id"])}
            ),
            Span(
                task["text"],
                cls="completed" if task["completed"] else ""
            ),
            Button(
                "Delete",
                {f"data-on-click": TaskManager.delete_task(task["id"])}
            )
        )

# Usage in FastHTML route
@rt("/")
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
```

### Signal System Deep Dive

StarModel provides multiple ways to access signals:

```python
class Counter(Entity):
    count: int = 0
    user_name: str = ""
    
    # Access patterns:
    # 1. Instance access: counter.count (returns actual value)
    # 2. Class signal access: Counter.count_signal (returns "$Counter.count")
    # 3. Method calls: Counter.increment() (returns "@get('/Counter/increment')")

# In templates, use the signal strings:
Div({f"data-text": Counter.count_signal})  # data-text="$Counter.count"
Button({f"data-on-click": Counter.increment()})  # data-on-click="@get('/Counter/increment')"
```

## Complete Datastar Attributes Reference

### 1. Signals Management (`data-signals`)

**Purpose**: Initialize and merge reactive signals
**StarModel Integration**: Auto-generated from Entity instances

```python
class DashboardEntity(Entity):
    total_sales: int = 0
    revenue: float = 0.0
    active_users: int = 0
    notifications: List[str] = []

@rt("/dashboard")
def dashboard(req: Request):
    dashboard = DashboardEntity.get(req)
    
    # Manual signals (if needed)
    manual_signals = {
        "theme": "dark",
        "sidebar_open": False
    }
    
    return Div(
        {f"data-signals": json.dumps(manual_signals)},  # Manual signals
        {f"data-signals__ifmissing": json.dumps(dashboard.signals)}  # Only set if missing
    )(
        dashboard,  # Auto-renders with signals
        H1({f"data-text": "'Dashboard - ' + ($theme || 'light') + ' theme'"}),
        
        # Stats display
        Div(cls="stats")(
            Div(cls="stat")(
                H3("Total Sales"),
                Span({f"data-text": DashboardEntity.total_sales_signal})
            ),
            Div(cls="stat")(
                H3("Revenue"),
                Span({f"data-text": f"'$' + {DashboardEntity.revenue_signal}.toFixed(2)"})
            ),
            Div(cls="stat")(
                H3("Active Users"),
                Span({f"data-text": DashboardEntity.active_users_signal})
            )
        )
    )
```

### 2. Data Binding (`data-bind`)

**Purpose**: Two-way data binding between form elements and signals
**StarModel Integration**: Use `ModelClass.field_signal` for binding

```python
class UserProfile(Entity):
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    age: int = 0
    preferences: Dict = {"theme": "light", "notifications": True}
    tags: List[str] = []

    @event
    def save_profile(self):
        # Validation
        if not self.email or "@" not in self.email:
            return Div(cls="error")("Invalid email address")
        
        # Save logic here
        return Div(cls="success")("Profile saved successfully!")

@rt("/profile")
def profile_form(req: Request):
    profile = UserProfile.get(req)
    
    return Form({f"data-on-submit": UserProfile.save_profile()})(
        # Text inputs
        Input(
            {f"data-bind": UserProfile.first_name_signal},
            placeholder="First Name",
            type="text"
        ),
        Input(
            {f"data-bind": UserProfile.last_name_signal},
            placeholder="Last Name"
        ),
        
        # Email with validation
        Input(
            {f"data-bind": UserProfile.email_signal},
            type="email",
            placeholder="Email"
        ),
        
        # Number input
        Input(
            {f"data-bind": UserProfile.age_signal},
            type="number",
            min="0",
            max="120"
        ),
        
        # Nested object binding
        Select({f"data-bind": "preferences.theme"})(
            Option("light", value="light"),
            Option("dark", value="dark")
        ),
        
        # Checkbox for boolean
        Label()(
            Input(
                type="checkbox",
                {f"data-bind": "preferences.notifications"}
            ),
            "Enable notifications"
        ),
        
        # Multiple checkboxes for array
        Fieldset()(
            Legend("Tags"),
            Label()(
                Input(type="checkbox", {f"data-bind": UserProfile.tags_signal}, value="developer"),
                "Developer"
            ),
            Label()(
                Input(type="checkbox", {f"data-bind": UserProfile.tags_signal}, value="designer"),
                "Designer"
            ),
            Label()(
                Input(type="checkbox", {f"data-bind": UserProfile.tags_signal}, value="manager"),
                "Manager"
            )
        ),
        
        # Submit button
        Button("Save Profile", type="submit")
    )
```

### 3. Event Handling (`data-on-*`)

**Purpose**: Execute expressions when events occur
**StarModel Integration**: Use `ModelClass.method()` for event handlers

```python
class InteractiveDemo(Entity):
    click_count: int = 0
    search_query: str = ""
    last_key: str = ""
    mouse_pos: Dict = {"x": 0, "y": 0}
    form_data: Dict = {}
    
    @event
    def increment_clicks(self, amount: int = 1):
        self.click_count += amount
    
    @event(method="post")
    def search(self, query: str = ""):
        self.search_query = query
        # Simulate search results
        return Div(id="search-results")(
            H3(f"Results for: {query}"),
            *[Div(f"Result {i}: {query} item") for i in range(3)]
        )
    
    @event
    def log_key(self, key: str):
        self.last_key = key
    
    @event
    def save_form(self, **form_data):
        self.form_data = form_data
        return Div(cls="success")("Form saved!")

@rt("/interactive")
def interactive_demo(req: Request):
    demo = InteractiveDemo.get(req)
    
    return Div(
        demo,  # Entity signals
        
        # Click events with modifiers
        Div(cls="click-demo")(
            H3("Click Events"),
            Button(
                "Click me",
                {f"data-on-click": InteractiveDemo.increment_clicks()}
            ),
            Button(
                "Add 5",
                {f"data-on-click": InteractiveDemo.increment_clicks(5)}
            ),
            Button(
                "Reset (once only)",
                {f"data-on-click__once": "$click_count = 0"}
            ),
            P({f"data-text": f"'Clicked: ' + {InteractiveDemo.click_count_signal} + ' times'"})
        ),
        
        # Debounced input
        Div(cls="search-demo")(
            H3("Debounced Search"),
            Input(
                {f"data-bind": InteractiveDemo.search_query_signal},
                {f"data-on-input__debounce.300ms": InteractiveDemo.search()},
                placeholder="Search... (debounced)"
            ),
            Div(id="search-results")
        ),
        
        # Keyboard events
        Div(cls="keyboard-demo")(
            H3("Keyboard Events"),
            Input(
                {f"data-on-keydown": InteractiveDemo.log_key("evt.key")},
                placeholder="Type here..."
            ),
            P({f"data-text": f"'Last key: ' + {InteractiveDemo.last_key_signal}"})
        ),
        
        # Form events with validation
        Form({f"data-on-submit__prevent": InteractiveDemo.save_form()})(
            H3("Form Events"),
            Input(name="username", placeholder="Username", required=True),
            Input(name="email", type="email", placeholder="Email", required=True),
            Button("Save", type="submit")
        ),
        
        # Window and outside events
        Div(
            {f"data-on-click__window": "$window_clicks = ($window_clicks || 0) + 1"},
            {f"data-on-click__outside": "$clicked_outside = true"},
            cls="event-capture"
        )(
            P("Window clicks: ", Span({f"data-text": "$window_clicks || 0"})),
            P("Clicked outside: ", Span({f"data-text": "$clicked_outside ? 'Yes' : 'No'"}))
        ),
        
        # Intersection observer
        Div(
            {f"data-on-intersect__once": InteractiveDemo.load_more()},
            cls="lazy-load"
        )("Scroll to load more..."),
        
        # Interval events
        Div({f"data-on-interval__duration.1s": "$timestamp = Date.now()"})(
            "Live timestamp: ",
            Span({f"data-text": "new Date($timestamp).toLocaleTimeString()"})
        )
    )
```

### 4. Dynamic Content (`data-text`, `data-show`)

**Purpose**: Dynamic text content and conditional visibility
**StarModel Integration**: Direct signal interpolation

```python
class ContentDemo(Entity):
    user_name: str = "Guest"
    user_score: int = 0
    show_advanced: bool = False
    items: List[Dict] = []
    current_time: str = ""
    
    @event
    def toggle_advanced(self):
        self.show_advanced = not self.show_advanced
    
    @event
    def add_item(self, name: str):
        self.items.append({"id": len(self.items) + 1, "name": name})

@rt("/content")
def content_demo(req: Request):
    content = ContentDemo.get(req)
    
    return Div(
        content,  # Entity signals
        
        # Dynamic text with expressions
        H1({f"data-text": f"'Welcome, ' + {ContentDemo.user_name_signal}"}),
        P({f"data-text": f"'Your score: ' + {ContentDemo.user_score_signal} + '/100'"}),
        P({f"data-text": f"{ContentDemo.user_score_signal} >= 80 ? 'Excellent!' : 'Keep trying!'"}),
        
        # Complex text expressions
        Div({f"data-text": f"""
            'You have ' + {ContentDemo.items_signal}.length + ' items. ' +
            ({ContentDemo.items_signal}.length === 0 ? 'Add your first item!' : 
             {ContentDemo.items_signal}.length === 1 ? 'Add more items!' : 
             'Great collection!')
        """}),
        
        # Conditional visibility
        Button(
            "Toggle Advanced Features",
            {f"data-on-click": ContentDemo.toggle_advanced()}
        ),
        
        # Show/hide based on boolean
        Div(
            {f"data-show": ContentDemo.show_advanced_signal},
            cls="advanced-panel"
        )(
            H3("Advanced Features"),
            P("These are advanced options for power users."),
            Button("Advanced Action", cls="btn-primary")
        ),
        
        # Show based on conditions
        Div({f"data-show": f"{ContentDemo.user_score_signal} > 50"})(
            "Congratulations! You've passed the halfway mark!"
        ),
        
        # Show for empty/non-empty entities
        Div({f"data-show": f"{ContentDemo.items_signal}.length === 0"})(
            "No items yet. Add some items to get started."
        ),
        
        Div({f"data-show": f"{ContentDemo.items_signal}.length > 0"})(
            H3("Your Items:"),
            Ul(id="items-list")(
                # Items populated by signals
            )
        ),
        
        # Form to add items
        Form({f"data-on-submit": ContentDemo.add_item()})(
            Input(name="name", placeholder="Item name"),
            Button("Add Item", type="submit")
        )
    )
```

### 5. CSS Classes and Styling (`data-class`, `data-attr`)

**Purpose**: Dynamic CSS classes and HTML attributes
**StarModel Integration**: Reactive styling based on entity

```python
class StylingDemo(Entity):
    theme: str = "light"
    is_loading: bool = False
    validation_errors: List[str] = []
    progress: int = 0
    status: str = "idle"  # idle, processing, success, error
    
    @event
    def toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"
    
    @event
    async def process_data(self):
        self.status = "processing"
        self.is_loading = True
        
        # Simulate processing with progress updates
        for i in range(0, 101, 20):
            self.progress = i
            yield  # Update UI
            await asyncio.sleep(0.5)
        
        self.status = "success"
        self.is_loading = False
    
    @event
    def validate_form(self, email: str, password: str):
        self.validation_errors = []
        if not email or "@" not in email:
            self.validation_errors.append("Invalid email")
        if len(password) < 8:
            self.validation_errors.append("Password too short")

@rt("/styling")
def styling_demo(req: Request):
    styling = StylingDemo.get(req)
    
    return Div(
        styling,  # Entity signals
        
        # Theme-based styling
        Div(
            {f"data-class": f"{{'theme-light': {StylingDemo.theme_signal} === 'light', 'theme-dark': {StylingDemo.theme_signal} === 'dark'}}"},
            cls="app-container"
        )(
            # Dynamic classes based on entity
            Button(
                {f"data-text": f"'Switch to ' + ({StylingDemo.theme_signal} === 'light' ? 'dark' : 'light') + ' theme'"},
                {f"data-on-click": StylingDemo.toggle_theme()},
                {f"data-class": f"{{'btn-primary': {StylingDemo.theme_signal} === 'light', 'btn-secondary': {StylingDemo.theme_signal} === 'dark'}}"}
            ),
            
            # Loading entities with dynamic attributes
            Div(
                {f"data-class": f"{{'loading': {StylingDemo.is_loading_signal}, 'success': {StylingDemo.status_signal} === 'success'}}"},
                {f"data-attr": f"{{'aria-busy': {StylingDemo.is_loading_signal}, 'data-status': {StylingDemo.status_signal}}}"}
            )(
                Button(
                    {f"data-text": f"{StylingDemo.is_loading_signal} ? 'Processing...' : 'Start Process'"},
                    {f"data-on-click": StylingDemo.process_data()},
                    {f"data-attr": f"{{'disabled': {StylingDemo.is_loading_signal}}}"}
                ),
                
                # Progress bar
                Div(
                    {f"data-show": StylingDemo.is_loading_signal},
                    cls="progress-container"
                )(
                    Div(
                        {f"data-attr": f"{{'style': 'width: ' + {StylingDemo.progress_signal} + '%'}}"},
                        cls="progress-bar"
                    ),
                    Span({f"data-text": f"{StylingDemo.progress_signal} + '%'"})
                )
            ),
            
            # Form validation with error styling
            Form({f"data-on-submit": StylingDemo.validate_form()})(
                Div(cls="form-group")(
                    Input(
                        name="email",
                        type="email",
                        placeholder="Email",
                        {f"data-class": f"{{'error': {StylingDemo.validation_errors_signal}.some(e => e.includes('email'))}}"}
                    )
                ),
                Div(cls="form-group")(
                    Input(
                        name="password",
                        type="password",
                        placeholder="Password",
                        {f"data-class": f"{{'error': {StylingDemo.validation_errors_signal}.some(e => e.includes('Password'))}}"}
                    )
                ),
                
                # Error display
                Div(
                    {f"data-show": f"{StylingDemo.validation_errors_signal}.length > 0"},
                    cls="error-list"
                )(
                    # Errors will be populated via signals
                ),
                
                Button("Validate", type="submit")
            )
        )
    )
```

### 6. Loading Entitys (`data-indicator`)

**Purpose**: Track loading entities during SSE requests
**StarModel Integration**: Automatic loading indicators for @event methods

```python
class LoadingDemo(Entity):
    data: List[Dict] = []
    upload_progress: int = 0
    save_status: str = ""
    
    @event
    async def fetch_data(self):
        """Long-running data fetch with loading entity"""
        # Simulate API call
        await asyncio.sleep(2)
        self.data = [{"id": i, "name": f"Item {i}"} for i in range(10)]
        return Div(id="data-list")(
            *[Div(f"Item: {item['name']}") for item in self.data]
        )
    
    @event
    async def save_data(self, **form_data):
        """Save with progress tracking"""
        self.save_status = "Saving..."
        
        # Simulate save process
        for i in range(0, 101, 25):
            await asyncio.sleep(0.3)
            self.save_status = f"Saving... {i}%"
            yield
        
        self.save_status = "Saved successfully!"
        return Div(cls="success")(self.save_status)
    
    @event
    async def upload_file(self):
        """File upload with progress"""
        for progress in range(0, 101, 10):
            self.upload_progress = progress
            yield Div(id="upload-progress")(
                f"Uploading: {progress}%"
            )
            await asyncio.sleep(0.2)

@rt("/loading")
def loading_demo(req: Request):
    loading = LoadingDemo.get(req)
    
    return Div(
        loading,  # Entity signals
        
        # Button with loading indicator
        Button(
            {f"data-on-click": LoadingDemo.fetch_data()},
            {f"data-indicator": "fetchingData"}  # Creates $fetchingData signal
        )(
            Span({f"data-show": "!$fetchingData"})("Fetch Data"),
            Span({f"data-show": "$fetchingData"})("Loading...")
        ),
        
        # Data display area
        Div(id="data-list"),
        
        # Form with save indicator
        Form({f"data-on-submit": LoadingDemo.save_data()})(
            Input(name="title", placeholder="Title"),
            Input(name="description", placeholder="Description"),
            Button(
                {f"data-indicator": "saving"},
                {f"data-attr": f"{{'disabled': '$saving'}}"}
            )(
                Span({f"data-show": "!$saving"})("Save"),
                Span({f"data-show": "$saving"})("Saving...")
            )
        ),
        
        # Upload with progress
        Button(
            {f"data-on-click": LoadingDemo.upload_file()},
            {f"data-indicator": "uploading"}
        )(
            Span({f"data-show": "!$uploading"})("Upload File"),
            Span({f"data-show": "$uploading"})("Uploading...")
        ),
        
        Div(id="upload-progress"),
        
        # Multiple loading entities
        Div(
            {f"data-class": f"{{'loading': '$fetchingData || $saving || $uploading'}}"},
            cls="status-panel"
        )(
            P("Global loading entity: "),
            Span({f"data-text": "'Active: ' + ($fetchingData ? 'fetching ' : '') + ($saving ? 'saving ' : '') + ($uploading ? 'uploading' : '') || 'none'"})
        )
    )
```

### 7. Persistence (`data-persist`)

**Purpose**: Persist signals in browser storage
**StarModel Integration**: Configurable via EntityStore

```python
class PersistenceDemo(Entity):
    model_config = {
        "store": EntityStore.CLIENT_LOCAL,  # or CLIENT_SESSION, SERVER_MEMORY
        "sync_with_client": True
    }
    
    user_preferences: Dict = {
        "theme": "light",
        "language": "en",
        "notifications": True
    }
    shopping_cart: List[Dict] = []
    session_data: Dict = {"last_visited": ""}
    
    @event
    def add_to_cart(self, item_id: str, name: str, price: float):
        self.shopping_cart.append({
            "id": item_id,
            "name": name,
            "price": price,
            "quantity": 1
        })
    
    @event
    def update_preferences(self, **prefs):
        self.user_preferences.update(prefs)

# Different persistence strategies
class SessionEntity(Entity):
    model_config = {"store": EntityStore.CLIENT_SESSION}  # sessionStorage
    temp_data: str = ""

class LocalEntity(Entity):
    model_config = {"store": EntityStore.CLIENT_LOCAL}   # localStorage
    persistent_data: str = ""

class ServerEntity(Entity):
    model_config = {"store": EntityStore.SERVER_MEMORY}  # Server memory
    server_data: str = ""

@rt("/persistence")
def persistence_demo(req: Request):
    # Different entity instances with different persistence
    session_entity = SessionEntity.get(req)
    local_entity = LocalEntity.get(req)
    server_entity = ServerEntity.get(req)
    
    return Div(
        # Manual persistence configuration
        Div(
            {f"data-signals": '{"manual_data": ""}'},
            {f"data-persist": "manual_data"}  # Persist specific signal
        ),
        
        Div(
            {f"data-signals": '{"session_only": ""}'},
            {f"data-persist__session": "session_only"}  # Session storage
        ),
        
        # Entity instances with auto-persistence
        session_entity,  # Auto-persists in sessionStorage
        local_entity,    # Auto-persists in localStorage
        server_entity,   # Auto-persists on server
        
        H2("Session Storage (cleared on tab close)"),
        Input(
            {f"data-bind": SessionEntity.temp_data_signal},
            placeholder="Session data"
        ),
        
        H2("Local Storage (persistent across sessions)"),
        Input(
            {f"data-bind": LocalEntity.persistent_data_signal},
            placeholder="Persistent data"
        ),
        
        H2("Server Memory (shared across clients)"),
        Input(
            {f"data-bind": ServerEntity.server_data_signal},
            placeholder="Server data"
        ),
        
        # Manual persistence controls
        H2("Manual Persistence"),
        Input(
            {f"data-bind": "manual_data"},
            placeholder="Manually persisted data"
        ),
        Input(
            {f"data-bind": "session_only"},
            placeholder="Session only data"
        )
    )
```

### 8. Element References (`data-ref`)

**Purpose**: Create signals that reference DOM elements
**StarModel Integration**: Access DOM elements in event handlers

```python
class RefDemo(Entity):
    scroll_position: int = 0
    element_info: Dict = {}
    
    @event
    def analyze_element(self, datastar: DatastarPayload):
        """Access DOM element data sent via datastar"""
        # Element data would be sent via datastar payload
        self.element_info = datastar.get("elementData", {})
    
    @event
    def scroll_to_top(self):
        # Server-side logic, client handles scrolling
        self.scroll_position = 0

@rt("/refs")
def refs_demo(req: Request):
    refs = RefDemo.get(req)
    
    return Div(
        refs,  # Entity signals
        
        # Create element references
        Div(
            {f"data-ref": "headerElement"},  # Creates $headerElement signal
            cls="header"
        )("Header Element"),
        
        Div(
            {f"data-ref": "contentElement"},
            cls="content",
            style="height: 200px; overflow-y: scroll;"
        )(
            # Long content for scrolling
            *[P(f"Paragraph {i}") for i in range(50)]
        ),
        
        # Use refs in other attributes
        Button(
            {f"data-on-click": "$headerElement.scrollIntoView({behavior: 'smooth'})"}
        )("Scroll to Header"),
        
        Button(
            {f"data-on-click": "$contentElement.scrollTop = 0"}
        )("Scroll Content to Top"),
        
        # Get element properties
        Button(
            {f"data-on-click": "$elementWidth = $headerElement.offsetWidth; $elementHeight = $headerElement.offsetHeight"}
        )("Get Element Size"),
        
        Div(
            {f"data-text": "'Header size: ' + ($elementWidth || 0) + 'x' + ($elementHeight || 0)"}
        ),
        
        # Focus management
        Input(
            {f"data-ref": "focusInput"},
            placeholder="Input element"
        ),
        Button(
            {f"data-on-click": "$focusInput.focus()"}
        )("Focus Input")
    )
```

### 9. Custom Validation (`data-custom-validity`)

**Purpose**: Set custom validation messages
**StarModel Integration**: Server-side validation with client feedback

```python
class ValidationDemo(Entity):
    username: str = ""
    email: str = ""
    password: str = ""
    confirm_password: str = ""
    validation_errors: Dict[str, str] = {}
    
    @event
    def validate_username(self, username: str):
        """Real-time username validation"""
        self.username = username
        if len(username) < 3:
            self.validation_errors["username"] = "Username must be at least 3 characters"
        elif " " in username:
            self.validation_errors["username"] = "Username cannot contain spaces"
        else:
            self.validation_errors.pop("username", None)
    
    @event
    def validate_email(self, email: str):
        """Email validation"""
        self.email = email
        if not email:
            self.validation_errors["email"] = "Email is required"
        elif "@" not in email:
            self.validation_errors["email"] = "Invalid email format"
        else:
            self.validation_errors.pop("email", None)
    
    @event
    def validate_passwords(self, password: str, confirm_password: str):
        """Password matching validation"""
        self.password = password
        self.confirm_password = confirm_password
        
        if len(password) < 8:
            self.validation_errors["password"] = "Password must be at least 8 characters"
        else:
            self.validation_errors.pop("password", None)
        
        if password != confirm_password:
            self.validation_errors["confirm_password"] = "Passwords do not match"
        else:
            self.validation_errors.pop("confirm_password", None)

@rt("/validation")
def validation_demo(req: Request):
    validation = ValidationDemo.get(req)
    
    return Form(
        validation,  # Entity signals
        
        # Username field with custom validation
        Div(cls="form-group")(
            Label("Username"),
            Input(
                {f"data-bind": ValidationDemo.username_signal},
                {f"data-on-input__debounce.300ms": ValidationDemo.validate_username()},
                {f"data-custom-validity": f"{ValidationDemo.validation_errors_signal}.username || ''"},
                name="username",
                placeholder="Username"
            ),
            Div(
                {f"data-show": f"{ValidationDemo.validation_errors_signal}.username"},
                {f"data-text": f"{ValidationDemo.validation_errors_signal}.username"},
                cls="error-message"
            )
        ),
        
        # Email field
        Div(cls="form-group")(
            Label("Email"),
            Input(
                {f"data-bind": ValidationDemo.email_signal},
                {f"data-on-input__debounce.300ms": ValidationDemo.validate_email()},
                {f"data-custom-validity": f"{ValidationDemo.validation_errors_signal}.email || ''"},
                type="email",
                name="email",
                placeholder="Email"
            ),
            Div(
                {f"data-show": f"{ValidationDemo.validation_errors_signal}.email"},
                {f"data-text": f"{ValidationDemo.validation_errors_signal}.email"},
                cls="error-message"
            )
        ),
        
        # Password fields
        Div(cls="form-group")(
            Label("Password"),
            Input(
                {f"data-bind": ValidationDemo.password_signal},
                {f"data-on-input__debounce.300ms": ValidationDemo.validate_passwords()},
                {f"data-custom-validity": f"{ValidationDemo.validation_errors_signal}.password || ''"},
                type="password",
                name="password",
                placeholder="Password"
            )
        ),
        
        Div(cls="form-group")(
            Label("Confirm Password"),
            Input(
                {f"data-bind": ValidationDemo.confirm_password_signal},
                {f"data-on-input__debounce.300ms": ValidationDemo.validate_passwords()},
                {f"data-custom-validity": f"{ValidationDemo.validation_errors_signal}.confirm_password || ''"},
                type="password",
                name="confirm_password",
                placeholder="Confirm Password"
            )
        ),
        
        # Submit button - disabled if any validation errors
        Button(
            "Submit",
            {f"data-attr": f"{{'disabled': 'Object.keys({ValidationDemo.validation_errors_signal}).length > 0'}}"},
            type="submit"
        ),
        
        # Overall form validation status
        Div(
            {f"data-show": f"Object.keys({ValidationDemo.validation_errors_signal}).length > 0"},
            cls="form-errors"
        )(
            P("Please fix the following errors:"),
            Ul(
                {f"data-text": f"Object.values({ValidationDemo.validation_errors_signal}).map(err => '<li>' + err + '</li>').join('')"}
            )
        )
    )
```

### 10. Advanced Attributes

```python
class AdvancedDemo(Entity):
    items: List[Dict] = []
    current_view: str = "list"
    
    @event
    async def load_more_items(self):
        """Lazy loading via intersection observer"""
        new_items = [
            {"id": len(self.items) + i, "name": f"Item {len(self.items) + i}"}
            for i in range(5)
        ]
        self.items.extend(new_items)
        
        return Div(id="items-container")(
            *[Div(f"Item: {item['name']}") for item in self.items[-5:]]
        )

@rt("/advanced")
def advanced_demo(req: Request):
    advanced = AdvancedDemo.get(req)
    
    return Div(
        advanced,  # Entity signals
        
        # URL entity management
        Div({f"data-replace-url": f"'/advanced?view=' + {AdvancedDemo.current_view_signal}"}),
        
        # Scroll into view
        Button(
            {f"data-scroll-into-view__smooth__vcenter": "true"},
            {f"data-on-click": "$scrolled = true"}
        )("Scroll to me"),
        
        # View transition
        Button(
            {f"data-on-click__viewtransition": f"{AdvancedDemo.current_view_signal} = 'grid'"}
        )("Switch to Grid View"),
        
        # Preserve attributes during morph
        Div(
            {f"data-preserve-attrs": "class style"},
            cls="dynamic-content",
            style="transition: all 0.3s ease;"
        )("This content preserves styling"),
        
        # Ignore morph for certain elements
        Div({f"data-ignore-morph": "true"})(
            "This element won't be morphed",
            Input(placeholder="User input preserved")
        ),
        
        # Lazy loading with intersection observer
        Div(id="items-container")(
            *[Div(f"Item: {item['name']}") for item in advanced.items]
        ),
        
        Div(
            {f"data-on-intersect__once": AdvancedDemo.load_more_items()},
            style="height: 50px; background: #f0f0f0; text-align: center; padding: 20px;"
        )("Scroll to load more items..."),
        
        # JSON signals for debugging
        Details(
            Summary("Debug: JSON Signals"),
            Pre({f"data-json-signals": "true"})
        )
    )
```

## Event Handling & Server-Side Integration

### The @event Decorator Deep Dive

```python
class ProductCatalog(Entity):
    products: List[Dict] = []
    filters: Dict = {"category": "", "min_price": 0, "max_price": 1000}
    sort_by: str = "name"
    page: int = 1
    
    # Basic event - auto-creates GET /ProductCatalog/load_products
    @event
    def load_products(self):
        """Load products with current filters"""
        filtered = self._apply_filters()
        return Div(id="products-grid")(
            *[self.product_card(p) for p in filtered]
        )
    
    # Custom HTTP method and path
    @event(method="post", path="/api/products/filter")
    def filter_products(self, category: str = "", min_price: int = 0, max_price: int = 1000):
        """Filter products - custom endpoint"""
        self.filters.update({
            "category": category,
            "min_price": min_price,
            "max_price": max_price
        })
        self.page = 1  # Reset pagination
        return self.load_products()
    
    # Async event with streaming updates
    @event(method="post")
    async def batch_update_products(self, updates: List[Dict]):
        """Update multiple products with progress"""
        total = len(updates)
        for i, update in enumerate(updates):
            # Process update
            self._update_product(update)
            
            # Send progress update
            progress = int((i + 1) / total * 100)
            yield Div(id="progress")(f"Progress: {progress}%")
            
            # Yield updated product
            yield self.product_card(update)
            
            await asyncio.sleep(0.1)  # Simulate processing time
        
        # Final completion message
        yield Div(id="status", cls="success")("All products updated!")
    
    # Event with custom selector and merge mode
    @event(selector="#product-detail", merge_mode="inner")
    def show_product_detail(self, product_id: int):
        """Show product detail in specific element"""
        product = next(p for p in self.products if p["id"] == product_id)
        return Div(
            H3(product["name"]),
            P(product["description"]),
            P(f"Price: ${product['price']}")
        )
    
    # Parameter injection examples
    @event
    def handle_request(self, request: Request, session: dict, datastar: DatastarPayload):
        """Access FastHTML's dependency injection"""
        user_id = session.get("user_id")
        signals = datastar.raw_data
        
        # Use request info
        user_agent = request.headers.get("user-agent", "")
        
        return Div(f"User {user_id} from {user_agent}")
    
    def product_card(self, product):
        """Reusable product component"""
        return Div(cls="product-card", id=f"product-{product['id']}")(
            H4(product["name"]),
            P(f"${product['price']}"),
            Button(
                "View Details",
                {f"data-on-click": ProductCatalog.show_product_detail(product["id"])}
            )
        )
    
    def _apply_filters(self):
        """Internal method for filtering logic"""
        filtered = self.products
        
        if self.filters["category"]:
            filtered = [p for p in filtered if p["category"] == self.filters["category"]]
        
        filtered = [p for p in filtered 
                   if self.filters["min_price"] <= p["price"] <= self.filters["max_price"]]
        
        return filtered
```

### URL Generation and Event Calling

```python
# StarModel automatically generates URL methods for each @event
class BlogPost(Entity):
    title: str = ""
    content: str = ""
    tags: List[str] = []
    
    @event(method="post")
    def save_draft(self, title: str, content: str):
        self.title = title
        self.content = content
        return Div("Draft saved!")
    
    @event(method="put", path="/blog/publish")
    def publish(self, tags: List[str] = None):
        self.tags = tags or []
        return Div("Post published!")

# Usage in templates:
@rt("/blog/editor")
def blog_editor(req: Request):
    blog = BlogPost.get(req)
    
    return Form(
        blog,  # Entity signals
        
        # These automatically generate the correct URLs:
        Input(
            {f"data-bind": BlogPost.title_signal},
            {f"data-on-input__debounce.1s": BlogPost.save_draft()},  # Auto: @post('/BlogPost/save_draft')
            name="title"
        ),
        
        Textarea(
            {f"data-bind": BlogPost.content_signal},
            {f"data-on-input__debounce.2s": BlogPost.save_draft()},
            name="content"
        ),
        
        Button(
            "Publish",
            {f"data-on-click": BlogPost.publish()}  # Auto: @put('/blog/publish')
        )
    )

# Manual URL generation (if needed):
# BlogPost.save_draft("My Title", "Content") → "@post('/BlogPost/save_draft?title=My%20Title&content=Content')"
```

## Advanced Entity Management Patterns

### Multi-Model Coordination

```python
class User(Entity):
    id: str = ""
    name: str = ""
    email: str = ""
    
    @event
    def update_profile(self, name: str, email: str):
        self.name = name
        self.email = email
        
        # Trigger updates in other models
        return [
            Div(id="user-profile")(f"Updated: {self.name}"),
            # Could trigger other model updates here
        ]

class NotificationService(Entity):
    notifications: List[Dict] = []
    
    @event
    def add_notification(self, message: str, type: str = "info"):
        self.notifications.append({
            "id": str(uuid.uuid4()),
            "message": message,
            "type": type,
            "timestamp": datetime.now().isoformat()
        })
    
    @event
    def dismiss_notification(self, notification_id: str):
        self.notifications = [n for n in self.notifications if n["id"] != notification_id]

class Dashboard(Entity):
    current_user_id: str = ""
    active_notifications: bool = True
    
    @event
    async def refresh_dashboard(self, user_id: str):
        """Coordinate multiple models"""
        self.current_user_id = user_id
        
        # Get other model instances
        user = User.get(self._current_request, id=user_id)
        notifications = NotificationService.get(self._current_request)
        
        # Trigger coordinated updates
        yield Div(id="user-section")(
            H2(f"Welcome, {user.name}"),
            P(f"Email: {user.email}")
        )
        
        yield Div(id="notifications-section")(
            *[
                Div(cls=f"notification {n['type']}", id=f"notif-{n['id']}")(
                    n["message"],
                    Button(
                        "×",
                        {f"data-on-click": NotificationService.dismiss_notification(n["id"])}
                    )
                )
                for n in notifications.notifications
            ]
        )

@rt("/dashboard")
def dashboard(req: Request):
    dashboard = Dashboard.get(req)
    user = User.get(req)
    notifications = NotificationService.get(req)
    
    return Div(
        dashboard,      # Multiple entity instances
        user,
        notifications,
        
        # Coordinated interface
        H1("Dashboard"),
        
        Div(id="user-section"),
        Div(id="notifications-section"),
        
        # Trigger refresh
        Button(
            "Refresh",
            {f"data-on-click": Dashboard.refresh_dashboard(user.id)}
        )
    )
```

### Real-Time Collaboration

```python
class CollaborativeEditor(Entity):
    document_id: str = ""
    content: str = ""
    cursors: Dict[str, Dict] = {}  # user_id -> {position, color}
    active_users: List[str] = []
    last_modified: str = ""
    
    @event
    async def join_session(self, user_id: str, document_id: str):
        """User joins collaborative session"""
        self.document_id = document_id
        if user_id not in self.active_users:
            self.active_users.append(user_id)
        
        # Broadcast to all users
        yield Div(id="active-users")(
            "Active users: " + ", ".join(self.active_users)
        )
    
    @event
    async def update_content(self, content: str, user_id: str, cursor_pos: int):
        """Real-time content updates"""
        self.content = content
        self.last_modified = datetime.now().isoformat()
        
        # Update cursor position
        self.cursors[user_id] = {
            "position": cursor_pos,
            "color": self._get_user_color(user_id)
        }
        
        # Broadcast to all clients
        yield Div(id="editor-content")(
            # Content with cursor overlays
            self._render_content_with_cursors()
        )
        
        yield Div(id="last-modified")(
            f"Last modified: {self.last_modified} by {user_id}"
        )
    
    @event
    async def live_cursor_update(self, user_id: str, cursor_pos: int):
        """Live cursor position updates"""
        if user_id in self.cursors:
            self.cursors[user_id]["position"] = cursor_pos
        
        # Send only cursor updates (more efficient)
        yield Div(id="cursors-overlay")(
            *[
                Div(
                    cls="cursor",
                    style=f"left: {pos['position']}px; border-color: {pos['color']}"
                )(user)
                for user, pos in self.cursors.items()
            ]
        )
    
    def _render_content_with_cursors(self):
        """Render content with collaborative cursors"""
        return Div(cls="editor-content")(
            Textarea(
                self.content,
                {f"data-bind": CollaborativeEditor.content_signal},
                {f"data-on-input__debounce.100ms": CollaborativeEditor.update_content()},
                {f"data-on-cursor": CollaborativeEditor.live_cursor_update()}
            ),
            Div(id="cursors-overlay")(
                *[
                    Div(
                        cls="cursor",
                        style=f"left: {pos['position']}px; border-color: {pos['color']}"
                    )(user)
                    for user, pos in self.cursors.items()
                ]
            )
        )

# Usage in collaborative document editor
@rt("/editor/{document_id}")
def collaborative_editor(req: Request, document_id: str):
    editor = CollaborativeEditor.get(req, document_id=document_id)
    user_id = req.session.get("user_id", "anonymous")
    
    return Div(
        editor,  # Entity with real-time updates
        
        # Auto-join session
        Div({f"data-on-load": CollaborativeEditor.join_session(user_id, document_id)}),
        
        H1(f"Editing Document: {document_id}"),
        
        Div(id="active-users"),
        Div(id="editor-content"),
        Div(id="last-modified")
    )
```

## Production-Ready Examples

### E-commerce Shopping Cart

```python
class ShoppingCart(Entity):
    model_config = {
        "store": EntityStore.CLIENT_LOCAL,  # Persist cart across sessions
        "sync_with_client": True
    }
    
    items: List[Dict] = []
    discount_code: str = ""
    discount_amount: float = 0.0
    shipping_cost: float = 0.0
    tax_rate: float = 0.08
    
    @property
    def subtotal(self) -> float:
        return sum(item["price"] * item["quantity"] for item in self.items)
    
    @property
    def total(self) -> float:
        subtotal = self.subtotal
        tax = subtotal * self.tax_rate
        return subtotal - self.discount_amount + self.shipping_cost + tax
    
    @event
    def add_item(self, product_id: str, name: str, price: float, quantity: int = 1):
        """Add item to cart or update quantity"""
        existing = next((item for item in self.items if item["id"] == product_id), None)
        
        if existing:
            existing["quantity"] += quantity
        else:
            self.items.append({
                "id": product_id,
                "name": name,
                "price": price,
                "quantity": quantity
            })
        
        return self.cart_summary()
    
    @event
    def update_quantity(self, product_id: str, quantity: int):
        """Update item quantity"""
        if quantity <= 0:
            return self.remove_item(product_id)
        
        for item in self.items:
            if item["id"] == product_id:
                item["quantity"] = quantity
                break
        
        return self.cart_summary()
    
    @event
    def remove_item(self, product_id: str):
        """Remove item from cart"""
        self.items = [item for item in self.items if item["id"] != product_id]
        return self.cart_summary()
    
    @event
    async def apply_discount(self, code: str):
        """Apply discount code with validation"""
        self.discount_code = code
        
        # Simulate API call to validate discount
        await asyncio.sleep(0.5)
        
        valid_codes = {"SAVE10": 10, "WELCOME20": 20, "STUDENT15": 15}
        
        if code in valid_codes:
            self.discount_amount = self.subtotal * (valid_codes[code] / 100)
            return Div(cls="success")(f"Discount applied: {code}")
        else:
            self.discount_amount = 0
            return Div(cls="error")(f"Invalid discount code: {code}")
    
    @event
    async def calculate_shipping(self, zip_code: str):
        """Calculate shipping cost"""
        # Simulate shipping calculation
        await asyncio.sleep(1)
        
        # Simple shipping logic
        if zip_code.startswith(("9", "8")):  # West coast
            self.shipping_cost = 15.0
        elif zip_code.startswith(("0", "1", "2")):  # East coast
            self.shipping_cost = 12.0
        else:
            self.shipping_cost = 10.0
        
        return self.cart_summary()
    
    def cart_summary(self):
        """Return cart summary component"""
        return Div(id="cart-summary")(
            H3(f"Cart ({len(self.items)} items)"),
            
            # Items list
            Div(cls="cart-items")(
                *[
                    Div(cls="cart-item", id=f"item-{item['id']}")(
                        Span(item["name"]),
                        Span(f"${item['price']:.2f}"),
                        Input(
                            type="number",
                            value=item["quantity"],
                            min="1",
                            {f"data-on-change": ShoppingCart.update_quantity(item["id"], "evt.target.value")}
                        ),
                        Button(
                            "Remove",
                            {f"data-on-click": ShoppingCart.remove_item(item["id"])}
                        )
                    )
                    for item in self.items
                ]
            ),
            
            # Totals
            Div(cls="cart-totals")(
                Div(f"Subtotal: ${self.subtotal:.2f}"),
                Div(f"Discount: -${self.discount_amount:.2f}") if self.discount_amount > 0 else "",
                Div(f"Shipping: ${self.shipping_cost:.2f}") if self.shipping_cost > 0 else "",
                Div(f"Tax: ${self.subtotal * self.tax_rate:.2f}"),
                H4(f"Total: ${self.total:.2f}")
            )
        )

@rt("/cart")
def shopping_cart_page(req: Request):
    cart = ShoppingCart.get(req)
    
    return Main(
        cart,  # Auto-persisted cart entity
        
        H1("Shopping Cart"),
        
        # Cart contents
        Div(id="cart-summary"),
        
        # Discount code form
        Form({f"data-on-submit": ShoppingCart.apply_discount()})(
            H3("Discount Code"),
            Input(
                name="code",
                {f"data-bind": ShoppingCart.discount_code_signal},
                placeholder="Enter discount code"
            ),
            Button(
                "Apply",
                {f"data-indicator": "applying_discount"},
                type="submit"
            )
        ),
        
        # Shipping calculator
        Form({f"data-on-submit": ShoppingCart.calculate_shipping()})(
            H3("Shipping Calculator"),
            Input(
                name="zip_code",
                placeholder="ZIP Code"
            ),
            Button(
                "Calculate Shipping",
                {f"data-indicator": "calculating_shipping"},
                type="submit"
            )
        ),
        
        # Checkout button
        Button(
            "Proceed to Checkout",
            {f"data-attr": f"{{'disabled': '{ShoppingCart.items_signal}.length === 0'}}"},
            {f"data-on-click": "@get('/checkout')"},
            cls="btn-primary"
        )
    )
```

### Real-Time Chat Application

```python
class ChatRoom(Entity):
    model_config = {
        "store": EntityStore.SERVER_MEMORY,  # Shared across all clients
        "auto_persist": True
    }
    
    room_id: str = ""
    messages: List[Dict] = []
    active_users: List[Dict] = []
    typing_users: List[str] = []
    
    @event
    async def join_room(self, user_id: str, username: str, room_id: str):
        """User joins chat room"""
        self.room_id = room_id
        
        # Add user if not already present
        if not any(u["id"] == user_id for u in self.active_users):
            self.active_users.append({
                "id": user_id,
                "username": username,
                "joined_at": datetime.now().isoformat()
            })
        
        # Add system message
        self.messages.append({
            "id": str(uuid.uuid4()),
            "type": "system",
            "content": f"{username} joined the room",
            "timestamp": datetime.now().isoformat()
        })
        
        # Broadcast updates
        yield self.render_messages()
        yield self.render_user_list()
    
    @event
    async def send_message(self, user_id: str, username: str, content: str):
        """Send message to room"""
        if not content.strip():
            return
        
        message = {
            "id": str(uuid.uuid4()),
            "type": "message",
            "user_id": user_id,
            "username": username,
            "content": content.strip(),
            "timestamp": datetime.now().isoformat()
        }
        
        self.messages.append(message)
        
        # Remove user from typing list
        if user_id in self.typing_users:
            self.typing_users.remove(user_id)
        
        # Broadcast message
        yield self.render_messages()
        yield self.render_typing_indicator()
    
    @event
    async def update_typing(self, user_id: str, is_typing: bool):
        """Update typing indicator"""
        if is_typing and user_id not in self.typing_users:
            self.typing_users.append(user_id)
        elif not is_typing and user_id in self.typing_users:
            self.typing_users.remove(user_id)
        
        yield self.render_typing_indicator()
    
    @event
    async def leave_room(self, user_id: str, username: str):
        """User leaves chat room"""
        # Remove from active users
        self.active_users = [u for u in self.active_users if u["id"] != user_id]
        
        # Remove from typing users
        if user_id in self.typing_users:
            self.typing_users.remove(user_id)
        
        # Add system message
        self.messages.append({
            "id": str(uuid.uuid4()),
            "type": "system",
            "content": f"{username} left the room",
            "timestamp": datetime.now().isoformat()
        })
        
        yield self.render_messages()
        yield self.render_user_list()
        yield self.render_typing_indicator()
    
    def render_messages(self):
        """Render messages list"""
        return Div(id="messages-list", cls="messages")(
            *[
                Div(
                    cls=f"message {msg['type']}",
                    id=f"msg-{msg['id']}"
                )(
                    Div(cls="message-header")(
                        Strong(msg.get("username", "System")),
                        Span(cls="timestamp")(
                            datetime.fromisoformat(msg["timestamp"]).strftime("%H:%M")
                        )
                    ) if msg["type"] != "system" else "",
                    Div(cls="message-content")(msg["content"])
                )
                for msg in self.messages[-50:]  # Last 50 messages
            ]
        )
    
    def render_user_list(self):
        """Render active users list"""
        return Div(id="users-list")(
            H4(f"Users ({len(self.active_users)})"),
            *[
                Div(cls="user")(
                    Span(user["username"]),
                    Span(cls="status online")("●")
                )
                for user in self.active_users
            ]
        )
    
    def render_typing_indicator(self):
        """Render typing indicator"""
        if not self.typing_users:
            return Div(id="typing-indicator")
        
        usernames = [
            u["username"] for u in self.active_users 
            if u["id"] in self.typing_users
        ]
        
        if len(usernames) == 1:
            text = f"{usernames[0]} is typing..."
        elif len(usernames) == 2:
            text = f"{usernames[0]} and {usernames[1]} are typing..."
        else:
            text = "Several people are typing..."
        
        return Div(id="typing-indicator", cls="typing")(text)

class UserSession(Entity):
    model_config = {"store": EntityStore.CLIENT_SESSION}
    
    user_id: str = ""
    username: str = ""
    current_room: str = ""
    message_draft: str = ""

@rt("/chat/{room_id}")
def chat_room_page(req: Request, room_id: str):
    session = UserSession.get(req)
    chat = ChatRoom.get(req, room_id=room_id)
    
    # Initialize user session if needed
    if not session.user_id:
        session.user_id = str(uuid.uuid4())
        session.username = f"User{random.randint(1000, 9999)}"
    
    return Div(
        session,  # User session entity
        chat,     # Shared chat entity
        
        # Auto-join room on load
        Div({f"data-on-load": ChatRoom.join_room(session.user_id, session.username, room_id)}),
        
        # Auto-leave room on page unload
        Div({f"data-on-beforeunload__window": ChatRoom.leave_room(session.user_id, session.username)}),
        
        Div(cls="chat-container")(
            # Messages area
            Div(cls="messages-panel")(
                H2(f"Room: {room_id}"),
                Div(id="messages-list"),
                Div(id="typing-indicator")
            ),
            
            # Users sidebar
            Div(cls="users-panel")(
                Div(id="users-list")
            ),
            
            # Message input
            Div(cls="input-panel")(
                Form({f"data-on-submit": ChatRoom.send_message(session.user_id, session.username)})(
                    Input(
                        name="content",
                        {f"data-bind": UserSession.message_draft_signal},
                        {f"data-on-input__debounce.300ms": ChatRoom.update_typing(session.user_id, True)},
                        {f"data-on-blur": ChatRoom.update_typing(session.user_id, False)},
                        placeholder="Type a message...",
                        cls="message-input"
                    ),
                    Button("Send", type="submit")
                )
            )
        )
    )
```

This comprehensive guide demonstrates how StarModel revolutionizes reactive web development by unifying entity management and event handling in entity-centric Python classes. The combination of Pydantic models, automatic SSE endpoints, and seamless Datastar integration eliminates the complexity of modern web development while providing powerful real-time capabilities.

**Key Benefits:**
- **Zero Configuration**: `@event` methods automatically become reactive endpoints
- **Type Safety**: Full Pydantic validation and typing throughout
- **Automatic Persistence**: Configurable entity storage (client/server)
- **Real-Time Updates**: Built-in SSE streaming with signal synchronization
- **FastHTML Integration**: Seamless dependency injection and component rendering

**Best Practices:**
1. Start with simple Entity classes and add complexity incrementally
2. Use descriptive event method names that map to user actions
3. Leverage StarModel's automatic URL generation for consistent routing
4. Choose appropriate storage strategies based on data sensitivity and sharing needs
5. Implement proper error handling and validation in event methods
6. Use async events for long-running operations with progress updates

StarModel enables building sophisticated reactive applications entirely in Python, making it ideal for AI developer agents who need to rapidly prototype and deploy interactive web applications without frontend complexity.