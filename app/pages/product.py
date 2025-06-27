from starmodel import *
from fasthtml.common import *
from monsterui.all import *

rt = APIRouter()

class Product(Entity):
    """Record-scoped entity - tied to specific product records."""
    model_config = {
        "arbitrary_types_allowed": True,
        "starmodel_auto_persist": True,
        "starmodel_persistence_backend": MemoryRepo(),
        "starmodel_ttl": 7200,
    }
    
    name: str = ""
    price: float = 0.0
    description: str = ""
    in_stock: bool = True
    
    @classmethod
    def _generate_entity_id(cls, req, **kwargs):
        # Generate product-specific ID from URL path
        product_id = req.path_params.get('id', 'default') if req else 'default'
        return f"product_{product_id}"
    
    @event
    def update_product(self, name: str, price: float, description: str):
        self.name = name
        self.price = price
        self.description = description
        return Div("Product updated!", cls="text-green-600 font-bold")
    
    @event
    def toggle_stock(self):
        self.in_stock = not self.in_stock
        status = "in stock" if self.in_stock else "out of stock"
        return Div(f"Product marked as {status}!", cls="text-blue-600 font-bold")

@rt('/product/{record_id}')
def product_detail(req: Request, sess: dict, record_id: int, auth: str = None):
    """
    Product detail page with record-scoped entity.
    Demonstrates entity tied to specific database records.
    """
    # Entity automatically injected by FastHTML integration
    product = Product.get(req)

    # Initialize product data if empty (simulating database load)
    if not product.name:
        product.name = f"Sample Product {record_id}"
        product.price = 19.99
        product.description = f"This is a sample product with ID {record_id}"
    
    return Titled(f"Product {record_id}",
        Main(
            Div(
                H1(f"📦 Product {record_id}", cls="text-3xl font-bold mb-6"),
                
                # Product entity display
                product,
                # Product information
                Div(
                    H2("Product Details", cls="text-xl font-bold mb-4"),
                    Div(
                        Div("Name: ", Span(data_text="$name"), cls="mb-2 font-bold"),
                        Div("Price: $", Span(data_text="$price"), cls="mb-2"),
                        Div("Description: ", Span(data_text="$description"), cls="mb-2"),
                        Div("In Stock: ", Span(data_text="$in_stock"), cls="mb-2"),
                        Div(f"Product ID: {record_id}", cls="text-sm text-gray-600"),
                        cls="bg-gray-100 p-4 rounded mb-6"
                    ),
                    cls="mb-6"
                ),
                
                # Product management (if user has permissions)
                Div(
                    H3("Product Management", cls="text-lg font-bold mb-4"),
                    Form(
                        Input(value=product.name, name="name", placeholder="Product Name", 
                              cls="border rounded px-3 py-2 mb-3 w-full"),
                        Input(value=product.price, name="price", placeholder="Price", type="number", step="0.01",
                              cls="border rounded px-3 py-2 mb-3 w-full"),
                        Input(value=product.description, name="description", placeholder="Description", 
                              cls="border rounded px-3 py-2 mb-3 w-full"),
                        Button("Update Product", type="submit", 
                               cls="bg-green-500 text-white px-6 py-2 rounded mr-2"),
                        data_on_submit=Product.update_product()
                    ),
                    Button("Toggle Stock Status", 
                           data_on_click=Product.toggle_stock(),
                           cls="bg-blue-500 text-white px-4 py-2 rounded mt-4"),
                    cls="mb-6"
                ),
                
                # Navigation
                Div(
                    A("← Back to Home", href="/", cls="text-blue-500 hover:underline mr-4"),
                    A("📦 Product 456", href="/product/456", cls="text-green-500 hover:underline mr-4"),
                    A("📦 Product 789", href="/product/789", cls="text-green-500 hover:underline"),
                ),
                
                cls="container mx-auto p-8 max-w-2xl"
            )
        )
    )
