from fasthtml.common import *
from fasthtml.core import APIRouter
from fasthtml.svg import *
from monsterui.all import *
from monsterui.franken import Grid as Grd
from pages.templates import app_template
from starmodel import Entity, event
from .components.charts import Apex_Chart, ChartT, construct_script
from typing import List
from pydantic import BaseModel, computed_field

class Sale(BaseModel):
    name: str
    email: str
    amount: int

class Dashboard(Entity):
    sales: int = 0
    subscriptions: int = 0
    active_now: int = 0
    total_revenue: int = 0
    recent_sales: List[Sale] = []

    @computed_field
    @property
    def pct_change(self) -> str:
        change = 100 * (self.recent_sales[-1].amount - self.recent_sales[-2].amount) / self.recent_sales[-2].amount if len(self.recent_sales) > 1 else 0
        return f"{change:.2f}%"
    
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
        from fasthtml.common import Div, H3, P
        from monsterui.all import Card, DiceBearAvatar, TextPresets
        
        def AvatarItem(name, email, amount):
            return Div(cls="flex items-center")(
                DiceBearAvatar(name, 9, 9),
                Div(cls="ml-4 space-y-1")(
                    P(name, cls=TextPresets.bold_sm), P(email, cls=TextPresets.muted_sm)
                ),
                Div(amount, cls="ml-auto font-medium"),
            )
            
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
        from pages.components.charts import construct_script, ChartT
        
        script = construct_script(
                    chart_type=ChartT.area,
                    series=[
                        {"name": "2024", "data": [sale.amount for sale in self.recent_sales]},
                    ],
                    categories=[sale.name for sale in self.recent_sales],
                    fill={"type": "gradient", "gradient": {"shadeIntensity": 1, "opacityFrom": 0.4, "opacityTo": 0.1}},
                )
        return script



def InfoCard(title, value, change):
    return Div(Card(Div(value), P(change, cls=TextPresets.muted_sm), header=H4(title)))

rev = InfoCard("Total Revenue", H3("$",Span(data_text=Dashboard.Stotal_revenue)), Span(Span(data_text=Dashboard.Spct_change)," from last sales"))
sub = InfoCard("Subscriptions",H3(data_text=Dashboard.Ssales), Span(Span(data_text=Dashboard.Spct_change)," from last month"))
sal = InfoCard("Sales", H3("$",Span(data_text=Dashboard.Stotal_revenue)), Span(Span(data_text=Dashboard.Spct_change)," from last month"))
act = InfoCard("Active Now", H3(data_text=Dashboard.Ssales), Span(Span(data_text=Dashboard.Spct_change)," from last hour"))

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
    entity = Dashboard.get(request)
    return Div(cls="space-y-4")(
        entity,        
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
                                construct_script(
                                  chart_type=ChartT.area,
                                  series=[
                                      {"name": "2024", "data": [sale.amount for sale in entity.recent_sales]},
                                    ],
                                    categories=[sale.name for sale in entity.recent_sales],
                                    fill={"type": "gradient", "gradient": {"shadeIntensity": 1, "opacityFrom": 0.4, "opacityTo": 0.1}},
                                ),
                                cls='max-h-md',
                            )
                        ),
                        Form(
                            Input(type="text", name="name", data_bind="$name", placeholder="Name"),
                            Input(type="email", name="email", data_bind="$email", placeholder="Email"),
                            Input(type="number", name="amount", data_bind="$amount", placeholder="Amount"),
                            Button("Add Sales", type="submit"),
                            data_on_submit=Dashboard.add_sales(),
                            
                        ),
                        cls="col-span-4"
                    ),
                    entity.recent_sales_card(),
                    gap=4,
                    cols=7,
                ),
                cls="space-y-4",
            ),
            Li(
                top_info_row,
                Grd(
                    Card(H3("Analytics to show here..."), cls="col-span-4"),
                    entity.recent_sales_card(),
                    gap=4,
                    cols=7,
                ),
                cls="space-y-4",
            ),
        ),
        id="content",
    )