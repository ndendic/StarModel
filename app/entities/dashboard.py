"""
Dashboard Entity

Domain logic for sales dashboard with metrics, recent sales tracking, and analytics.
"""

from typing import List
from pydantic import BaseModel, computed_field
from starmodel import Entity, event

class Sale(BaseModel):
    name: str
    email: str
    amount: int

class DashboardEntity(Entity):
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