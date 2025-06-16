from fasthtml.common import *
from monsterui.all import *
from starmodel import *
from pages.templates import page_template
import random

rt = APIRouter()

class Docs(Entity):
    """Documentation page for StarModel."""
    pass


# load md files from docs folder
docs_folder = Path(__file__).parent.parent / "assets" / "docs"
md_files = [f for f in docs_folder.glob("*.md")]


content = ""
for file in md_files:
    with open(file, "r") as f:
        content = f.read()


@rt("/docs")
@page_template(title="StarModel Docs")
def docs(req: Request):
    return Div(cls="font-serif max-w-2xl mx-auto")(
        H1("StarModel Docs"),
        P("This is the StarModel docs page."),
        render_md(content)
    )