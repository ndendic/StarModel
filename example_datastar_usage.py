#!/usr/bin/env python3
"""
Example demonstrating the enhanced Datastar parameter extraction in FastState.
Shows how to use DatastarPayload alongside FastHTML's parameter injection.
"""

from fasthtml.common import *
from faststate import State, event, DatastarPayload

class EnhancedFormState(State):
    """Example state demonstrating Datastar parameter extraction."""
    form_data: dict = {}
    user_preferences: dict = {}
    message: str = "Ready"
    counter: int = 0
    
    @event(method="post")
    def handle_form_submit(self, 
                          session: dict,              # FastHTML session injection
                          datastar: DatastarPayload,  # Datastar payload injection
                          user_id: int = 0,           # From query params or datastar
                          action: str = "submit"):    # From query params or datastar
        """
        Handle form submission with mixed parameter sources.
        
        Parameters can come from:
        - session: FastHTML session (auto-injected)
        - datastar: Datastar payload from form data or JSON
        - user_id: Query param or datastar payload
        - action: Query param or datastar payload
        """
        # Access session data (FastHTML injection)
        session_user = session.get('user', 'anonymous')
        
        # Access Datastar payload data
        if datastar:
            # Access as attributes
            form_name = datastar.form_name or "unnamed_form"
            form_values = datastar.form_values or {}
            
            # Access using dict methods
            extra_data = datastar.get('extra_data', {})
            validation_errors = datastar.get('validation_errors', [])
            
            # Access raw data
            all_datastar_data = datastar.raw_data
        else:
            form_name = "no_datastar"
            form_values = {}
            extra_data = {}
            validation_errors = []
            all_datastar_data = {}
        
        # Update state
        self.counter += 1
        self.form_data = {
            'form_name': form_name,
            'form_values': form_values,
            'user_id': user_id,
            'action': action,
            'session_user': session_user
        }
        
        self.message = f"Form '{form_name}' submitted by {session_user} (submission #{self.counter})"
        
        # Return UI update
        return Div(
            H3(f"Form Processed: {form_name}"),
            P(f"User: {session_user} (ID: {user_id})"),
            P(f"Action: {action}"),
            P(f"Values: {len(form_values)} fields"),
            P(f"Extra data: {len(extra_data)} items"),
            P(f"Validation errors: {len(validation_errors)}"),
            Pre(json.dumps(all_datastar_data, indent=2)),
            cls="bg-green-100 p-4 rounded"
        )
    
    @event
    def update_preference(self,
                         datastar: DatastarPayload,
                         auth: str = None,           # FastHTML auth injection
                         pref_key: str = "default"):
        """Update user preference with Datastar data."""
        
        if datastar and 'pref_value' in datastar:
            pref_value = datastar.pref_value
            
            # Update preferences
            if auth:
                self.user_preferences[f"{auth}_{pref_key}"] = pref_value
            else:
                self.user_preferences[pref_key] = pref_value
            
            self.message = f"Preference '{pref_key}' updated to '{pref_value}'"
            
            return Div(
                P(f"✅ Updated {pref_key} = {pref_value}"),
                P(f"Total preferences: {len(self.user_preferences)}"),
                cls="bg-blue-100 p-2 rounded"
            )
        else:
            self.message = "No preference data received"
            return Div(
                P("❌ No preference data in Datastar payload"),
                cls="bg-red-100 p-2 rounded"
            )
    
    @event
    def complex_interaction(self,
                           session: dict,              # FastHTML session
                           htmx: HtmxHeaders,          # FastHTML HTMX headers  
                           datastar: DatastarPayload,  # Datastar payload
                           request: Request,           # FastHTML request
                           mode: str = "standard"):     # Query param or datastar
        """
        Demonstrate complex parameter mixing.
        Shows all types of parameter injection working together.
        """
        # FastHTML injections
        is_htmx = bool(htmx.request) if htmx else False
        session_data = dict(session) if session else {}
        request_method = request.method
        request_url = str(request.url)
        
        # Datastar data
        if datastar:
            # Rich data from forms or client-side JavaScript
            interaction_data = {
                'click_count': datastar.get('click_count', 0),
                'mouse_position': datastar.get('mouse_position', {}),
                'form_state': datastar.get('form_state', {}),
                'user_selections': datastar.get('user_selections', []),
                'timestamp': datastar.get('timestamp'),
                'client_info': datastar.get('client_info', {})
            }
        else:
            interaction_data = {}
        
        # Update state with comprehensive info
        self.counter += 1
        self.message = f"Complex interaction #{self.counter} in {mode} mode"
        
        return Div(
            H3("Complex Interaction Results"),
            Div(
                H4("FastHTML Data:"),
                P(f"HTMX Request: {is_htmx}"),
                P(f"Method: {request_method}"),
                P(f"URL: {request_url}"),
                P(f"Session keys: {list(session_data.keys())}"),
                cls="mb-4"
            ),
            Div(
                H4("Datastar Data:"),
                P(f"Mode: {mode}"),
                P(f"Click count: {interaction_data.get('click_count', 'N/A')}"),
                P(f"Mouse position: {interaction_data.get('mouse_position', 'N/A')}"),
                P(f"Selections: {len(interaction_data.get('user_selections', []))}"),
                P(f"Timestamp: {interaction_data.get('timestamp', 'N/A')}"),
                cls="mb-4"
            ),
            Details(
                Summary("Raw Datastar Payload"),
                Pre(json.dumps(datastar.raw_data if datastar else {}, indent=2)),
                cls="mb-4"
            ),
            cls="bg-yellow-100 p-4 rounded"
        )

def demo_url_generation():
    """Demonstrate URL generation with Datastar parameter filtering."""
    print("🔗 URL Generation Examples:")
    print("=" * 40)
    
    # Basic form submit - only non-special params included
    url1 = EnhancedFormState.handle_form_submit(user_id=123, action="create")
    print(f"handle_form_submit(user_id=123, action='create'):")
    print(f"  → {url1}")
    print(f"  ✅ Includes: user_id, action")
    print(f"  ✅ Excludes: session, datastar (auto-injected)")
    print()
    
    # Preference update - filters datastar param
    url2 = EnhancedFormState.update_preference(pref_key="theme")
    print(f"update_preference(pref_key='theme'):")
    print(f"  → {url2}")
    print(f"  ✅ Includes: pref_key")
    print(f"  ✅ Excludes: datastar, auth (auto-injected)")
    print()
    
    # Complex interaction - filters all special params
    url3 = EnhancedFormState.complex_interaction(mode="advanced")
    print(f"complex_interaction(mode='advanced'):")
    print(f"  → {url3}")
    print(f"  ✅ Includes: mode")
    print(f"  ✅ Excludes: session, htmx, datastar, request (auto-injected)")

def main():
    """Demonstrate the enhanced Datastar parameter extraction."""
    print("🧪 Enhanced Datastar Parameter Extraction Example")
    print("=" * 60)
    
    print("\n📚 Key Features:")
    print("✅ DatastarPayload class for rich client data")
    print("✅ Automatic Datastar parameter extraction from:")
    print("   • Query parameter: ?datastar={json}")
    print("   • JSON request body")
    print("   • Form data with datastar field")
    print("✅ Mixed parameter injection:")
    print("   • FastHTML: session, auth, request, htmx")
    print("   • Datastar: payload data as attributes or dict")
    print("   • Regular: query params with type conversion")
    print("✅ Smart URL generation (filters auto-injected params)")
    
    print("\n💡 Usage Examples:")
    print()
    print("@event")
    print("def my_handler(self, session: dict, datastar: DatastarPayload, user_id: int):")
    print("    # session: Auto-injected FastHTML session")
    print("    # datastar: Rich client data as DatastarPayload object")
    print("    # user_id: From query params or datastar payload")
    print("    ")
    print("    user = session.get('user', 'anonymous')")
    print("    client_data = datastar.form_data if datastar else {}")
    print("    preferences = datastar.get('preferences', {}) if datastar else {}")
    print("    ")
    print("    # Process the data...")
    print()
    
    demo_url_generation()
    
    print("\n🎯 Benefits:")
    print("✅ Full FastHTML compatibility")
    print("✅ Rich client-side data access")
    print("✅ Type-safe parameter extraction")
    print("✅ Clean URL generation")
    print("✅ Flexible data sources (query, JSON, form)")

if __name__ == "__main__":
    main()