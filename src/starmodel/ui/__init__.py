import importlib
from functools import cached_property
from typing import Any, Mapping

from fastapi import Response

from .fastcore_utils import partition, risinstance

html_tags = ['A', 'P', 'I', 'B', 'H1','H2','H3','H4','H5','H6','Div','Span','Pre','Blockquote','Q','Ul','Ol','Li','Dl','Dt','Dd','Table','Thead','Tbody','Tfoot','Tr','Th','Td','Caption','Form','Label','Select','Option','Textarea','Button','Fieldset','Legend','Article','Section','Nav','Aside','Header','Footer','Main','Figure','Figcaption','Strong','Em','Mark','Code','Samp','Kbd','Var','Time','Abbr','Dfn','Sub','Sup','Audio','Video','Picture','Canvas','Details','Summary','Dialog','Script','Noscript','Template','Style','Head','Body']
self_closing_tags = ['Area','Base','Br','Col','Embed','Hr','Img','Input','Link','Meta','Param','Source','Track','Wbr']
case_sensitive_tags = 'A Animate AnimateMotion AnimateTransform Circle ClipPath Defs Desc Ellipse FeBlend FeColorMatrix FeComponentTransfer FeDropShadow FeComposite FeConvolveMatrix FeDiffuseLighting FeDisplacementMap FeDistantLight FeFlood FeFuncA FeFuncB FeFuncG FeFuncR FeGaussianBlur FeImage FeMerge FeMergeNode FeMorphology FeOffset FePointLight FeSpecularLighting FeSpotLight FeTile FeTurbulence Filter Font Font_face Font_face_format Font_face_name Font_face_src Font_face_uri ForeignObject G Glyph GlyphRef Hkern Image LinearGradient Marker Mask Metadata Missing_glyph Mpath Pattern RadialGradient Set Stop Switch Symbol TextPath Tref Tspan Use View Vkern' 

_specials = set('@.-!~:[](){}$%^&*+=|/?<>,`')

def attrmap(o):
    if _specials & set(o): return o
    o = dict(htmlClass='class', cls='class', _class='class', klass='class',
             _for='for', fr='for', htmlFor='for').get(o, o)
    return o if o=='_' else o.lstrip('_').replace('_', '-')


class Tag:
    def __init__(self, *args, **kwargs):
        """Sets four attributes, name, module, children, and attrs.
        These are important for Starlette view responses, as nested objects
        get auto-serialized to JSON and need to be rebuilt. Without
        the values of these attributes, the object reconstruction can't occur"""
        self._name = self.__class__.__name__
        self._module = self.__class__.__module__
        ds,c = partition(args, risinstance(Mapping))
        for d in ds: kwargs = {**kwargs, **d}
        self._children = c
        self._attrs = kwargs

        if self._children and self._name in self_closing_tags:
            raise RuntimeError(f"{self._name} element cannot have child elements because it represents self closing html tag.")

    
    @property
    def name(self) -> str:
        return self._name.lower()

    @property
    def attrs(self) -> str:
        if not self._attrs:
            return ""
        return " " + " ".join(f'{attrmap(k)}="{v}"' for k, v in self._attrs.items())

    @cached_property
    def children(self):
        return "".join(
            [c.render() if isinstance(c, Tag) else c for c in self._children]
        )

    def __repr__(self):
        return f"<{self.name}{self.attrs}>{self.children}</{self.name}>"
    
    def __str__(self):
        return self.__repr__()
    
    def _repr_html_(self):
        return self.__repr__()
    
    def render(self) -> str:
        return self.__repr__()


class CaseTag(Tag):
    """This is for case-sensitive tags like those used in SVG generation."""
    @property
    def name(self) -> str:
        return self._name[0].lower() + self._name[1:]
    

class Html(Tag):
    """Defines the root of an HTML document"""

    def __init__(self, *children, headers: list | None = (), bodykws: dict | None = {}, footers: list[Tag] | None = None, **kwargs):
        super().__init__(*children, **kwargs)
        self._headers = headers
        self._bodykws = bodykws
        self._footers = footers

    @property
    def headers(self):
        return "".join([c.render() if isinstance(c, Tag) else c for c in self._headers])

    @property
    def bodykws(self) -> str:
        if not self._bodykws:
            return ""
        return " " + " ".join(f'{attrmap(k)}="{v}"' for k, v in self._bodykws.items())
    
    @cached_property
    def footers(self):
        return "".join(
            [c.render() if isinstance(c, Tag) else c for c in self._footers]
        ) if self._footers else ""

    def __repr__(self) -> str:
        return f"""<!doctype html><html{self.attrs}><head>{self.headers}</head><body{self.bodykws}>{self.children}{self.footers}</body></html>"""




class RawHTML(Tag):
    """Custom tag for rendering raw HTML content without escaping."""

    def __init__(self, *args, **kwargs):
        """Initialize RawHTML with a single string argument.

        Args:
            *args: Should be exactly one string argument
            **kwargs: Ignored (for consistency with Tag interface)
        """
        if len(args) > 1:
            raise ValueError("RawHTML accepts only one string argument")

        html_string = args[0] if args else ""

        if not isinstance(html_string, str):
            raise TypeError("RawHTML only accepts string content")

        super().__init__(html_string)

    def __repr__(self) -> str:
        """Render the raw HTML string without escaping."""
        return self._children[0] if self._children else ""
    

for class_name in html_tags + self_closing_tags:
    new_class = type(class_name, (Tag,), {
        '__init__': Tag.__init__,
        '__repr__': Tag.__repr__, 
        '__str__': Tag.__str__,
        '_repr_html_': Tag._repr_html_,
        '__doc__': f"""Object that represents `<{class_name}>` HTML element.""",
        '_name': class_name
    })
    globals()[class_name] = new_class

for class_name in case_sensitive_tags.split():
    new_class = type(class_name, (CaseTag,), {
        '__init__': CaseTag.__init__,
        '__repr__': CaseTag.__repr__, 
        '__str__': CaseTag.__str__,
        '_repr_html_': CaseTag._repr_html_,
        '__doc__': f"""Object that represents `<{class_name}>` HTML element.""",
        '_name': class_name
    })  
    globals()[class_name] = new_class

def dict_to_ft_component(d):
    children_raw = d.get("_children", ())
    children = tuple(
        dict_to_ft_component(c) if isinstance(c, dict) else c for c in children_raw
    )
    module = importlib.import_module(d["_module"])
    obj = getattr(module, d["_name"])
    return obj(*children, **d.get("_attrs", {}))


class TagResponse(Response):
    """Custom response class to handle starmodel.ui.Tag."""

    media_type = "text/html; charset=utf-8"

    def render(self, content: Any) -> bytes:
        """Render Tag elements to bytes of HTML."""
        if isinstance(content, dict):
            content = dict_to_ft_component(content)
        return content.render().encode("utf-8")