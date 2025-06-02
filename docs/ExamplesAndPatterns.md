# FastState Examples and Usage Patterns

This document provides practical examples and proven patterns for building applications with FastState.

## Table of Contents

1. [Complete Application Examples](#complete-application-examples)
2. [Common UI Patterns](#common-ui-patterns)
3. [Data Management Patterns](#data-management-patterns)
4. [Authentication Patterns](#authentication-patterns)
5. [Real-time Features](#real-time-features)
6. [Performance Patterns](#performance-patterns)
7. [Testing Patterns](#testing-patterns)

---

## Complete Application Examples

### Todo Application

A complete todo application demonstrating CRUD operations, filtering, and real-time updates.

```python
from fasthtml.common import *
from faststate import State, event, StateScope, StateConfig, state_registry, initialize_faststate
from typing import List, Optional
from datetime import datetime
import json

# Initialize FastState
initialize_faststate()

class TodoItem:
    """Todo item data structure."""
    def __init__(self, id: str, text: str, completed: bool = False, created_at: datetime = None):
        self.id = id
        self.text = text
        self.completed = completed
        self.created_at = created_at or datetime.now()
    
    def to_dict(self):
        return {
            "id": self.id,
            "text": self.text,
            "completed": self.completed,
            "created_at": self.created_at.isoformat()
        }

class TodoState(State):
    """Todo application state with filtering and statistics."""
    items: List[dict] = Field(default_factory=list)
    filter_mode: str = "all"  # all, active, completed
    new_item_text: str = ""
    
    @property
    def active_count(self) -> int:
        return len([item for item in self.items if not item["completed"]])
    
    @property
    def completed_count(self) -> int:
        return len([item for item in self.items if item["completed"]])
    
    @property
    def filtered_items(self) -> List[dict]:
        if self.filter_mode == "active":
            return [item for item in self.items if not item["completed"]]
        elif self.filter_mode == "completed":
            return [item for item in self.items if item["completed"]]
        return self.items
    
    @event
    def add_item(self, text: str):
        """Add new todo item."""
        if not text.strip():
            return Div("Todo text cannot be empty", cls="error")
        
        new_item = TodoItem(
            id=str(uuid.uuid4()),
            text=text.strip()
        )
        self.items.append(new_item.to_dict())
        self.new_item_text = ""
    
    @event
    def toggle_item(self, item_id: str):
        """Toggle completion status of todo item."""
        for item in self.items:
            if item["id"] == item_id:
                item["completed"] = not item["completed"]
                break
    
    @event
    def delete_item(self, item_id: str):
        """Delete todo item."""
        self.items = [item for item in self.items if item["id"] != item_id]
    
    @event
    def edit_item(self, item_id: str, new_text: str):
        """Edit todo item text."""
        if not new_text.strip():
            return Div("Todo text cannot be empty", cls="error")
        
        for item in self.items:
            if item["id"] == item_id:
                item["text"] = new_text.strip()
                break
    
    @event
    def set_filter(self, filter_mode: str):
        """Set filter mode."""
        if filter_mode in ["all", "active", "completed"]:
            self.filter_mode = filter_mode
    
    @event
    def clear_completed(self):
        """Remove all completed items."""
        self.items = [item for item in self.items if not item["completed"]]
    
    @event
    def toggle_all(self):
        """Toggle all items to completed/active."""
        all_completed = all(item["completed"] for item in self.items)
        for item in self.items:
            item["completed"] = not all_completed
    
    def __ft__(self):
        """Render todo application UI."""
        return Div(
            # Header with input
            Header(
                H1("Todos", cls="text-3xl font-bold text-center mb-8"),
                Form(
                    Input(
                        value=self.new_item_text,
                        placeholder="What needs to be done?",
                        data_bind="$new_item_text",
                        cls="w-full p-3 border rounded-lg text-lg"
                    ),
                    Button(
                        "Add Todo",
                        type="submit",
                        cls="mt-2 px-4 py-2 bg-blue-500 text-white rounded"
                    ),
                    data_on_submit="add_item({text: $new_item_text})",
                    cls="mb-6"
                ),
                cls="mb-6"
            ),
            
            # Todo list
            Section(
                *[self._render_todo_item(item) for item in self.filtered_items],
                cls="space-y-2 mb-6"
            ) if self.items else Div("No todos yet!", cls="text-center text-gray-500 mb-6"),
            
            # Footer with stats and filters
            Footer(
                Div(
                    Span(f"{self.active_count} item{'s' if self.active_count != 1 else ''} left"),
                    cls="text-sm text-gray-600"
                ),
                
                # Filter buttons
                Div(
                    Button(
                        "All",
                        onclick="set_filter({filter_mode: 'all'})",
                        cls=f"px-3 py-1 mx-1 rounded {'bg-blue-500 text-white' if self.filter_mode == 'all' else 'bg-gray-200'}"
                    ),
                    Button(
                        "Active",
                        onclick="set_filter({filter_mode: 'active'})",
                        cls=f"px-3 py-1 mx-1 rounded {'bg-blue-500 text-white' if self.filter_mode == 'active' else 'bg-gray-200'}"
                    ),
                    Button(
                        "Completed",
                        onclick="set_filter({filter_mode: 'completed'})",
                        cls=f"px-3 py-1 mx-1 rounded {'bg-blue-500 text-white' if self.filter_mode == 'completed' else 'bg-gray-200'}"
                    ),
                    cls="flex justify-center"
                ),
                
                # Clear completed
                Div(
                    Button(
                        "Clear Completed",
                        onclick="clear_completed()",
                        cls="px-3 py-1 bg-red-500 text-white rounded text-sm"
                    ) if self.completed_count > 0 else "",
                    Button(
                        f"Toggle All ({'Uncheck' if all(item['completed'] for item in self.items) else 'Check'})",
                        onclick="toggle_all()",
                        cls="px-3 py-1 bg-gray-500 text-white rounded text-sm ml-2"
                    ) if self.items else "",
                ),
                
                cls="flex justify-between items-center text-sm"
            ),
            
            cls="max-w-md mx-auto p-6",
            data_signals=json.dumps(self.model_dump()),
            id="todo-app"
        )
    
    def _render_todo_item(self, item: dict):
        """Render individual todo item."""
        return Div(
            Input(
                type="checkbox",
                checked=item["completed"],
                onclick=f"toggle_item({{item_id: '{item['id']}'}})",
                cls="mr-3"
            ),
            Span(
                item["text"],
                cls=f"flex-1 {'line-through text-gray-500' if item['completed'] else ''}"
            ),
            Button(
                "×",
                onclick=f"delete_item({{item_id: '{item['id']}'}})",
                cls="ml-2 px-2 py-1 text-red-500 hover:bg-red-100 rounded"
            ),
            cls="flex items-center p-3 border rounded-lg hover:bg-gray-50",
            key=item["id"]
        )

# Register state
state_registry.register(TodoState, StateConfig(scope=StateScope.SESSION))

# FastHTML app setup
app, rt = fast_app()

@rt('/')
def home(todos: TodoState):
    """Todo application home page."""
    return Titled("Todo App", todos)

if __name__ == "__main__":
    serve(reload=True)
```

### E-commerce Product Catalog

A product catalog with cart functionality, search, and filtering.

```python
class Product:
    """Product data structure."""
    def __init__(self, id: int, name: str, price: float, category: str, description: str = ""):
        self.id = id
        self.name = name
        self.price = price
        self.category = category
        self.description = description
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "category": self.category,
            "description": self.description
        }

class ProductCatalogState(State):
    """Product catalog with search and filtering."""
    products: List[dict] = Field(default_factory=list)
    search_query: str = ""
    selected_category: str = "all"
    sort_by: str = "name"  # name, price, category
    sort_direction: str = "asc"  # asc, desc
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize with sample products
        if not self.products:
            self.products = [
                Product(1, "Laptop", 999.99, "Electronics", "High-performance laptop").to_dict(),
                Product(2, "Coffee Mug", 12.99, "Kitchen", "Ceramic coffee mug").to_dict(),
                Product(3, "Book", 19.99, "Books", "Programming guide").to_dict(),
                Product(4, "Headphones", 199.99, "Electronics", "Wireless headphones").to_dict(),
            ]
    
    @property
    def categories(self) -> List[str]:
        """Get unique categories."""
        return sorted(set(p["category"] for p in self.products))
    
    @property
    def filtered_products(self) -> List[dict]:
        """Get filtered and sorted products."""
        # Filter by search query
        filtered = self.products
        if self.search_query:
            query = self.search_query.lower()
            filtered = [
                p for p in filtered
                if query in p["name"].lower() or query in p["description"].lower()
            ]
        
        # Filter by category
        if self.selected_category != "all":
            filtered = [p for p in filtered if p["category"] == self.selected_category]
        
        # Sort
        reverse = self.sort_direction == "desc"
        if self.sort_by == "price":
            filtered.sort(key=lambda p: p["price"], reverse=reverse)
        elif self.sort_by == "category":
            filtered.sort(key=lambda p: p["category"], reverse=reverse)
        else:  # name
            filtered.sort(key=lambda p: p["name"], reverse=reverse)
        
        return filtered
    
    @event
    def update_search(self, query: str):
        """Update search query."""
        self.search_query = query
    
    @event
    def set_category(self, category: str):
        """Set selected category."""
        self.selected_category = category
    
    @event
    def set_sort(self, sort_by: str, direction: str = None):
        """Set sorting criteria."""
        self.sort_by = sort_by
        if direction:
            self.sort_direction = direction
    
    def __ft__(self):
        """Render product catalog."""
        return Div(
            # Search and filters
            Header(
                H1("Product Catalog", cls="text-3xl font-bold mb-6"),
                
                # Search bar
                Div(
                    Input(
                        value=self.search_query,
                        placeholder="Search products...",
                        data_bind="$search_query",
                        data_on_input="update_search({query: $search_query})",
                        cls="w-full p-3 border rounded-lg"
                    ),
                    cls="mb-4"
                ),
                
                # Filters
                Div(
                    # Category filter
                    Select(
                        Option("All Categories", value="all"),
                        *[Option(cat, value=cat) for cat in self.categories],
                        value=self.selected_category,
                        data_on_change="set_category({category: this.value})",
                        cls="p-2 border rounded mr-4"
                    ),
                    
                    # Sort options
                    Select(
                        Option("Sort by Name", value="name"),
                        Option("Sort by Price", value="price"),
                        Option("Sort by Category", value="category"),
                        value=self.sort_by,
                        data_on_change="set_sort({sort_by: this.value})",
                        cls="p-2 border rounded mr-4"
                    ),
                    
                    Button(
                        "↑↓" if self.sort_direction == "asc" else "↓↑",
                        onclick=f"set_sort({{sort_by: '{self.sort_by}', direction: '{('desc' if self.sort_direction == 'asc' else 'asc')}'}})",
                        cls="p-2 border rounded"
                    ),
                    
                    cls="flex items-center mb-6"
                ),
                
                cls="mb-8"
            ),
            
            # Product grid
            Div(
                *[self._render_product(product) for product in self.filtered_products],
                cls="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
            ) if self.filtered_products else Div(
                "No products found",
                cls="text-center text-gray-500 py-8"
            ),
            
            cls="max-w-6xl mx-auto p-6",
            data_signals=json.dumps(self.model_dump()),
            id="catalog"
        )
    
    def _render_product(self, product: dict):
        """Render individual product card."""
        return Div(
            Div(
                H3(product["name"], cls="text-xl font-bold mb-2"),
                P(f"${product['price']:.2f}", cls="text-lg text-green-600 font-semibold mb-2"),
                P(product["category"], cls="text-sm text-gray-500 mb-2"),
                P(product["description"], cls="text-gray-700 mb-4"),
                Button(
                    "Add to Cart",
                    onclick=f"add_to_cart({{product_id: {product['id']}}})",
                    cls="w-full bg-blue-500 text-white p-2 rounded hover:bg-blue-600"
                ),
                cls="p-4"
            ),
            cls="border rounded-lg shadow hover:shadow-lg transition-shadow"
        )

class ShoppingCartState(State):
    """Shopping cart state."""
    items: List[dict] = Field(default_factory=list)
    
    @property
    def total_items(self) -> int:
        return sum(item["quantity"] for item in self.items)
    
    @property
    def total_price(self) -> float:
        return sum(item["price"] * item["quantity"] for item in self.items)
    
    @event
    def add_to_cart(self, product_id: int):
        """Add product to cart."""
        # In real app, fetch product details from database
        product = get_product_by_id(product_id)  # Mock function
        
        # Check if item already in cart
        for item in self.items:
            if item["product_id"] == product_id:
                item["quantity"] += 1
                return
        
        # Add new item
        self.items.append({
            "product_id": product_id,
            "name": product["name"],
            "price": product["price"],
            "quantity": 1
        })
    
    @event
    def remove_from_cart(self, product_id: int):
        """Remove product from cart."""
        self.items = [item for item in self.items if item["product_id"] != product_id]
    
    @event
    def update_quantity(self, product_id: int, quantity: int):
        """Update item quantity."""
        if quantity <= 0:
            self.remove_from_cart(product_id)
            return
        
        for item in self.items:
            if item["product_id"] == product_id:
                item["quantity"] = quantity
                break

# Register states
state_registry.register(ProductCatalogState, StateConfig(scope=StateScope.GLOBAL))
state_registry.register(ShoppingCartState, StateConfig(scope=StateScope.SESSION))

# Routes
@rt('/')
def catalog(catalog: ProductCatalogState, cart: ShoppingCartState):
    """Product catalog page."""
    return Titled("E-commerce Demo",
        Div(
            # Cart indicator
            Div(
                f"Cart: {cart.total_items} items (${cart.total_price:.2f})",
                A("View Cart", href="/cart", cls="ml-4 text-blue-500"),
                cls="fixed top-4 right-4 bg-white border rounded-lg p-4 shadow"
            ),
            
            # Catalog
            catalog,
            
            # Hidden cart state for updates
            Div(
                data_signals=json.dumps(cart.model_dump()),
                id="cart-updates",
                style="display: none"
            )
        )
    )

@rt('/cart')
def cart_page(cart: ShoppingCartState):
    """Shopping cart page."""
    return Titled("Shopping Cart",
        cart.render_cart()  # Would implement render_cart method
    )
```

---

## Common UI Patterns

### Modal Dialog Management

```python
class ModalState(State):
    """State for managing modal dialogs."""
    is_open: bool = False
    title: str = ""
    content: str = ""
    modal_type: str = "info"  # info, warning, error, confirm
    
    @event
    def open_modal(self, title: str, content: str, modal_type: str = "info"):
        """Open modal with specified content."""
        self.is_open = True
        self.title = title
        self.content = content
        self.modal_type = modal_type
    
    @event
    def close_modal(self):
        """Close modal."""
        self.is_open = False
    
    @event(selector="#modal-container", merge_mode="morph")
    def confirm_action(self, action: str):
        """Handle confirmation actions."""
        # Process the confirmed action
        if action == "delete_user":
            # Perform deletion
            pass
        
        self.close_modal()
        return Div("Action completed!", cls="success-message")
    
    def __ft__(self):
        """Render modal overlay."""
        if not self.is_open:
            return Div()  # Empty when closed
        
        return Div(
            # Overlay
            Div(
                onclick="close_modal()",
                cls="fixed inset-0 bg-black bg-opacity-50 z-40"
            ),
            
            # Modal content
            Div(
                Header(
                    H2(self.title, cls="text-xl font-bold"),
                    Button(
                        "×",
                        onclick="close_modal()",
                        cls="text-gray-500 hover:text-gray-700"
                    ),
                    cls="flex justify-between items-center mb-4"
                ),
                
                Div(self.content, cls="mb-6"),
                
                Footer(
                    Button("OK", onclick="close_modal()", cls="px-4 py-2 bg-blue-500 text-white rounded mr-2"),
                    Button("Cancel", onclick="close_modal()", cls="px-4 py-2 bg-gray-300 rounded")
                    if self.modal_type == "confirm" else "",
                    cls="flex justify-end"
                ),
                
                cls=f"fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white p-6 rounded-lg shadow-xl z-50 max-w-md w-full modal-{self.modal_type}"
            ),
            
            id="modal-overlay"
        )

# Usage in routes
@rt('/users')
def users_page(modal: ModalState):
    """Users page with modal functionality."""
    return Titled("Users",
        Div(
            Button(
                "Delete User",
                onclick="open_modal({title: 'Confirm Delete', content: 'Are you sure?', modal_type: 'confirm'})",
                cls="bg-red-500 text-white px-4 py-2 rounded"
            ),
            
            # Modal overlay
            modal,
            
            data_signals=json.dumps(modal.model_dump()),
            id="users-page"
        )
    )
```

### Form Validation and Error Handling

```python
class ContactFormState(State):
    """Contact form with comprehensive validation."""
    # Form fields
    name: str = ""
    email: str = ""
    subject: str = ""
    message: str = ""
    
    # Validation state
    errors: dict = Field(default_factory=dict)
    touched: dict = Field(default_factory=dict)  # Track which fields were touched
    is_submitting: bool = False
    submission_status: str = ""  # success, error, or empty
    
    def validate_field(self, field: str, value: str) -> Optional[str]:
        """Validate individual field."""
        if field == "name":
            if not value.strip():
                return "Name is required"
            if len(value.strip()) < 2:
                return "Name must be at least 2 characters"
        
        elif field == "email":
            if not value.strip():
                return "Email is required"
            if not "@" in value or "." not in value.split("@")[-1]:
                return "Please enter a valid email address"
        
        elif field == "subject":
            if not value.strip():
                return "Subject is required"
        
        elif field == "message":
            if not value.strip():
                return "Message is required"
            if len(value.strip()) < 10:
                return "Message must be at least 10 characters"
        
        return None
    
    @event
    def update_field(self, field: str, value: str):
        """Update field value and validate if touched."""
        setattr(self, field, value)
        
        # Mark field as touched
        self.touched[field] = True
        
        # Validate if field was touched
        error = self.validate_field(field, value)
        if error:
            self.errors[field] = error
        else:
            self.errors.pop(field, None)
        
        # Clear submission status when editing
        if self.submission_status:
            self.submission_status = ""
    
    @event
    def validate_form(self):
        """Validate entire form."""
        self.errors = {}
        
        # Validate all fields
        for field in ["name", "email", "subject", "message"]:
            value = getattr(self, field)
            error = self.validate_field(field, value)
            if error:
                self.errors[field] = error
        
        return len(self.errors) == 0
    
    @event
    async def submit_form(self):
        """Submit form if validation passes."""
        # Mark all fields as touched
        self.touched = {field: True for field in ["name", "email", "subject", "message"]}
        
        if not self.validate_form():
            return
        
        self.is_submitting = True
        self.submission_status = ""
        
        try:
            # Simulate API call
            await send_contact_email(
                name=self.name,
                email=self.email,
                subject=self.subject,
                message=self.message
            )
            
            # Success - reset form
            self.name = self.email = self.subject = self.message = ""
            self.touched = {}
            self.errors = {}
            self.submission_status = "success"
            
        except Exception as e:
            self.submission_status = "error"
            self.errors["submit"] = f"Failed to send message: {str(e)}"
        
        finally:
            self.is_submitting = False
    
    def __ft__(self):
        """Render contact form with validation."""
        return Form(
            H2("Contact Us", cls="text-2xl font-bold mb-6"),
            
            # Name field
            Div(
                Label("Name", cls="block text-sm font-medium mb-1"),
                Input(
                    value=self.name,
                    data_bind="$name",
                    data_on_input="update_field({field: 'name', value: this.value})",
                    cls=f"w-full p-3 border rounded-lg {'border-red-500' if 'name' in self.errors else 'border-gray-300'}"
                ),
                Div(
                    self.errors.get("name", ""),
                    cls="text-red-500 text-sm mt-1"
                ) if "name" in self.errors else "",
                cls="mb-4"
            ),
            
            # Email field
            Div(
                Label("Email", cls="block text-sm font-medium mb-1"),
                Input(
                    type="email",
                    value=self.email,
                    data_bind="$email",
                    data_on_input="update_field({field: 'email', value: this.value})",
                    cls=f"w-full p-3 border rounded-lg {'border-red-500' if 'email' in self.errors else 'border-gray-300'}"
                ),
                Div(
                    self.errors.get("email", ""),
                    cls="text-red-500 text-sm mt-1"
                ) if "email" in self.errors else "",
                cls="mb-4"
            ),
            
            # Subject field
            Div(
                Label("Subject", cls="block text-sm font-medium mb-1"),
                Input(
                    value=self.subject,
                    data_bind="$subject",
                    data_on_input="update_field({field: 'subject', value: this.value})",
                    cls=f"w-full p-3 border rounded-lg {'border-red-500' if 'subject' in self.errors else 'border-gray-300'}"
                ),
                Div(
                    self.errors.get("subject", ""),
                    cls="text-red-500 text-sm mt-1"
                ) if "subject" in self.errors else "",
                cls="mb-4"
            ),
            
            # Message field
            Div(
                Label("Message", cls="block text-sm font-medium mb-1"),
                TextArea(
                    self.message,
                    data_bind="$message",
                    data_on_input="update_field({field: 'message', value: this.value})",
                    rows=4,
                    cls=f"w-full p-3 border rounded-lg {'border-red-500' if 'message' in self.errors else 'border-gray-300'}"
                ),
                Div(
                    self.errors.get("message", ""),
                    cls="text-red-500 text-sm mt-1"
                ) if "message" in self.errors else "",
                cls="mb-6"
            ),
            
            # Submit button
            Button(
                "Sending..." if self.is_submitting else "Send Message",
                type="submit",
                disabled=self.is_submitting or bool(self.errors),
                cls=f"w-full p-3 rounded-lg font-medium {'bg-gray-400 cursor-not-allowed' if self.is_submitting or self.errors else 'bg-blue-500 hover:bg-blue-600'} text-white"
            ),
            
            # Status messages
            Div(
                Div("Message sent successfully!", cls="text-green-600 font-medium")
                if self.submission_status == "success" else "",
                
                Div(
                    self.errors.get("submit", "Failed to send message"),
                    cls="text-red-500 font-medium"
                ) if self.submission_status == "error" else "",
                
                cls="mt-4"
            ),
            
            data_on_submit="submit_form()",
            data_signals=json.dumps(self.model_dump()),
            id="contact-form",
            cls="max-w-md mx-auto p-6"
        )
```

### Infinite Scroll and Pagination

```python
class PaginatedListState(State):
    """State for paginated list with infinite scroll."""
    items: List[dict] = Field(default_factory=list)
    page: int = 1
    page_size: int = 20
    total_items: int = 0
    is_loading: bool = False
    has_more: bool = True
    search_query: str = ""
    
    @property
    def total_pages(self) -> int:
        return (self.total_items + self.page_size - 1) // self.page_size
    
    @event
    async def load_more_items(self):
        """Load next page of items."""
        if self.is_loading or not self.has_more:
            return
        
        self.is_loading = True
        
        try:
            # Simulate API call
            response = await fetch_items(
                page=self.page + 1,
                page_size=self.page_size,
                search=self.search_query
            )
            
            # Append new items
            self.items.extend(response["items"])
            self.page += 1
            self.total_items = response["total"]
            self.has_more = len(self.items) < self.total_items
            
        except Exception as e:
            return Div(f"Error loading items: {e}", cls="error")
        
        finally:
            self.is_loading = False
    
    @event(selector="#items-container", merge_mode="inner")
    async def search_items(self, query: str):
        """Search items with new query."""
        self.search_query = query
        self.page = 1
        self.is_loading = True
        
        try:
            response = await fetch_items(
                page=1,
                page_size=self.page_size,
                search=query
            )
            
            self.items = response["items"]
            self.total_items = response["total"]
            self.has_more = len(self.items) < self.total_items
            
            # Return new items HTML
            return Div(
                *[self._render_item(item) for item in self.items],
                cls="space-y-4"
            )
            
        finally:
            self.is_loading = False
    
    def __ft__(self):
        """Render paginated list with infinite scroll."""
        return Div(
            # Search bar
            Input(
                value=self.search_query,
                placeholder="Search items...",
                data_bind="$search_query",
                data_on_input="search_items({query: this.value})",
                cls="w-full p-3 border rounded-lg mb-6"
            ),
            
            # Items container
            Div(
                *[self._render_item(item) for item in self.items],
                id="items-container",
                cls="space-y-4 mb-6"
            ),
            
            # Loading indicator
            Div(
                "Loading more items...",
                cls="text-center py-4"
            ) if self.is_loading else "",
            
            # Load more button
            Button(
                "Load More",
                onclick="load_more_items()",
                disabled=self.is_loading or not self.has_more,
                cls="w-full p-3 bg-blue-500 text-white rounded-lg disabled:bg-gray-400"
            ) if self.has_more and not self.is_loading else "",
            
            # Infinite scroll trigger (invisible element)
            Div(
                data_intersect="load_more_items()",
                style="height: 1px;",
                id="scroll-trigger"
            ),
            
            data_signals=json.dumps(self.model_dump()),
            id="paginated-list"
        )
    
    def _render_item(self, item: dict):
        """Render individual list item."""
        return Div(
            H3(item["title"], cls="text-lg font-bold"),
            P(item["description"], cls="text-gray-600"),
            cls="p-4 border rounded-lg"
        )
```

This documentation provides comprehensive examples and patterns for building real-world applications with FastState. Each pattern demonstrates best practices for state management, UI interaction, and real-time updates.