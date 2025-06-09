from fasthtml.common import *
from fasthtml.core import APIRouter
from fasthtml.svg import *
from monsterui.all import *
from monsterui.franken import Grid as Grd
from pages.templates import app_template
from starmodel import State, event
from .components.charts import Apex_Chart, ChartT
from pydantic import BaseModel

class Sale(BaseModel):
    name: str
    email: str
    amount: int

class DashboardState(State):
    
    sales: int = 0
    subscriptions: int = 0
    active_now: int = 0
    total_revenue: int = 0
    recent_sales: List[Sale] = []
    
    @event
    async def add_sales(self, amount: int = 0, name: str = "Unknown", email: str = "Unknown"):
        self.sales += 1
        self.total_revenue += amount
        sale = Sale(name=name, email=email, amount=amount)
        self.recent_sales.append(sale)
        yield self.recent_sales_card()
        yield self.sales_chart()


    @event
    def increment(self):
        self.count += 1
        return self.count
    
    def recent_sales_card(self):
        return Card(cls="col-span-3", id="recent-sales-card")(
            Div(cls="space-y-8 px-4")(
                *[
                    AvatarItem(n, e, d)
                    for (n, e, d) in (
                        *[(sale.name, sale.email, f"+${sale.amount}") for sale in self.recent_sales],
                    )
                ]
            ),
            header=Div(
                H3("Recent Sales"), P("You made 265 sales this month.", cls=TextPresets.muted_sm)
            ),
        )
    
    def sales_chart(self):
        return Div(id="sales-chart")(
                Apex_Chart(
                    chart_type=ChartT.area,
                    series=[
                        {"name": "2024", "data": [sale.amount for sale in self.recent_sales]},
                    ],
                    categories=[sale.name for sale in self.recent_sales],
                    fill={"type": "gradient", "gradient": {"shadeIntensity": 1, "opacityFrom": 0.4, "opacityTo": 0.1}},
                    cls='max-w-md max-h-md',
                )
            ),
    
def InfoCard(title, value, change):
    return Div(Card(Div(value), P(change, cls=TextPresets.muted_sm)), header=H4(title))


rev = InfoCard("Total Revenue", H3("$",Span(data_text=DashboardState.total_revenue_signal)), "+20.1% from last month")
sub = InfoCard("Subscriptions",H3(data_text=DashboardState.sales_signal), "+180.1% from last month")
sal = InfoCard("Sales", H3("+12,234"), "+19% from last month")
act = InfoCard("Active Now", H3("+573"), "+201 since last hour")

# %% ../example_dashboard.ipynb
top_info_row = Grd(rev, sub, sal, act, cols_min=1, cols_max=4)


def AvatarItem(name, email, amount):
    return Div(cls="flex items-center")(
        DiceBearAvatar(name, 9, 9),
        Div(cls="ml-4 space-y-1")(
            P(name, cls=TextPresets.bold_sm), P(email, cls=TextPresets.muted_sm)
        ),
        Div(amount, cls="ml-auto font-medium"),
    )



teams = [["Alicia Koch"], ["Acme Inc", "Monster Inc."], ["Create a Team"]]

opt_hdrs = ["Personal", "Team", ""]

team_dropdown = Select(
    Optgroup(label="Personal Account")(Option(A("Alicia Koch"))),
    Optgroup(label="Teams")(Option(A("Acme Inc")), Option(A("Monster Inc."))),
    Option(A("Create a Team")),
)


rt = APIRouter()


@rt("/dashboard")
@app_template("Dashboard")
def dashboard(request):
    state = DashboardState.get(request)
    return Div(cls="space-y-4")(
        state,
        H2("Dashboard"),
        TabContainer(
            Li(A("Overview", cls="uk-active")),
            Li(A("Analytics")),
            Li(A("Reports")),
            Li(A("Notifications")),
            uk_switcher="connect: #component-nav; animation:uk-anmt-fade",
            alt=True,
        ),
        Ul(id="component-nav", cls="uk-switcher")(
            Li(
                top_info_row,
                Grd(
                    Card(
                        H3("Overview to show here..."),
                        Div(id="sales-chart")(
                            Apex_Chart(
                                  chart_type=ChartT.area,
                                  series=[
                                      {"name": "2024", "data": [sale.amount for sale in state.recent_sales]},
                                  ],
                                  categories=[sale.name for sale in state.recent_sales],
                                  fill={"type": "gradient", "gradient": {"shadeIntensity": 1, "opacityFrom": 0.4, "opacityTo": 0.1}},
                                  cls='max-w-md max-h-md',
                            )
                        ),
                        Form(
                            Input(type="text", name="name", data_bind="$name", placeholder="Name"),
                            Input(type="email", name="email", data_bind="$email", placeholder="Email"),
                            Input(type="number", name="amount", data_bind="$amount", placeholder="Amount"),
                            Button("Add Sales", type="submit"),
                            data_on_submit=DashboardState.add_sales(),
                            
                        ),
                        cls="col-span-4"
                    ),
                    state.recent_sales_card(),
                    gap=4,
                    cols=7,
                ),
                cls="space-y-4",
            ),
            Li(
                top_info_row,
                Grd(
                    Card(H3("Analytics to show here..."), cls="col-span-4"),
                    state.recent_sales_card(),
                    gap=4,
                    cols=7,
                ),
                cls="space-y-4",
            ),
        ),
        id="content",
    )


# def find_base_table_class(table_name: str) -> type[BaseTable]:
#     for subclass in BaseTable.__subclasses__():
#         if subclass.__name__.lower() == table_name.lower():
#             return subclass
#     return None


# @rt("/table/{table}")
# def get(request, table: str = ""):
#     if table:
#         model: BaseTable = find_base_table_class(table)
#         if model:
#             if is_htmx(request):
#                 return model.render_table(request)
#             else:
#                 return app_page("Table", request, model.render_table(request))
#         else:
#             return Div(f"Model {table} not found.")
#     else:
#         return H1("Table not found")


# @rt("/table/{table}/search")
# def get(request, table: str = ""):
#     model: BaseTable = find_base_table_class(table)
#     if model:
#         return model.render_table(request, records_only=True)
#     else:
#         return H1("Table not found")


# @rt("/table/{table}/{record_id}")
# def get(request, table: str = "", record_id: str = ""):
#     model_class = find_base_table_class(table)
#     if model_class:
#         if record_id == "new":
#             return model_class()
#         else:
#             record = model_class.get(record_id)
#             if record:
#                 return record
#             else:
#                 return H1("Record not found")
#     else:
#         return H1("Table not found")


# @rt("/table/{table}/upsert")
# async def post(request, table: str = ""):
#     model: BaseTable = find_base_table_class(table)
#     form_data = await request.form()
#     processed_data = dict(form_data)

#     for key, value in processed_data.items():
#         if value == "on":  # If it's a checkbox value
#             processed_data[key] = True
#         elif value == "":  # If checkbox is unchecked, it won't be in form data
#             processed_data[key] = False

#     if model:
#         if model.upsert(processed_data):
#             return model.render_table(request, records_only=True)
#     else:
#         return H1("Table not found")


# @rt("/table/{table}/{record_id}")
# def delete(request, table: str = "", record_id: str = ""):
#     model: BaseTable = find_base_table_class(table)
#     if model:
#         model.delete_record(record_id)
#         return model.render_table(request, records_only=True)
#     else:
#         return H1("Table not found")
