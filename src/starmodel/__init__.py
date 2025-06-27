"""
StarModel - Reactive Entity Management for FastHTML

A powerful entity management system that integrates with FastHTML's dependency injection
to provide automatic entity management with scoping and real-time updates.
"""

# Import from new organized modules while maintaining backward compatibility
from .core import Entity, SQLEntity, event, datastar_script, DatastarPayload
from .persistence import (
    EntityPersistenceBackend, 
    MemoryRepo, get_memory_persistence,
    SQLModelBackend,
    start_all_cleanup, stop_all_cleanup, configure_all_cleanup
)
from .app import UnitOfWork, InProcessBus
from .ui import *

html_tags = ['A', 'P', 'I', 'B', 'H1','H2','H3','H4','H5','H6','Div','Span','Pre','Blockquote','Q','Ul','Ol','Li','Dl','Dt','Dd','Table','Thead','Tbody','Tfoot','Tr','Th','Td','Caption','Form','Label','Select','Option','Textarea','Button','Fieldset','Legend','Article','Section','Nav','Aside','Header','Footer','Main','Figure','Figcaption','Strong','Em','Mark','Code','Samp','Kbd','Var','Time','Abbr','Dfn','Sub','Sup','Audio','Video','Picture','Canvas','Details','Summary','Dialog','Script','Noscript','Template','Style','Head','Body']
self_closing_tags = ['Area','Base','Br','Col','Embed','Hr','Img','Input','Link','Meta','Param','Source','Track','Wbr']
case_sensitive_tags = 'A Animate AnimateMotion AnimateTransform Circle ClipPath Defs Desc Ellipse FeBlend FeColorMatrix FeComponentTransfer FeDropShadow FeComposite FeConvolveMatrix FeDiffuseLighting FeDisplacementMap FeDistantLight FeFlood FeFuncA FeFuncB FeFuncG FeFuncR FeGaussianBlur FeImage FeMerge FeMergeNode FeMorphology FeOffset FePointLight FeSpecularLighting FeSpotLight FeTile FeTurbulence Filter Font Font_face Font_face_format Font_face_name Font_face_src Font_face_uri ForeignObject G Glyph GlyphRef Hkern Image LinearGradient Marker Mask Metadata Missing_glyph Mpath Pattern RadialGradient Set Stop Switch Symbol TextPath Tref Tspan Use View Vkern' 


# Import new application service layer components
# from .adapters.fasthtml import include_entity, register_entities, register_all_entities

__all__ = [
    # Core entity components
    'Entity',
    'SQLEntity',
    'event',
    'datastar_script',
    'DatastarPayload',
    # 'entities_rt',
    
    # Application service layer
    'UnitOfWork',
    'InProcessBus',
    
    # Adapters
    'EntityPersistenceBackend',
    'MemoryRepo',
    'get_memory_persistence',
    'SQLModelBackend',
    'start_all_cleanup',
    'stop_all_cleanup', 
    'configure_all_cleanup',
    
    # UI
    'Tag',
    'TagResponse',
    'CaseTag',
    'Html',
    'RawHTML',
    *html_tags,
    *self_closing_tags,
    *case_sensitive_tags.split(),
]