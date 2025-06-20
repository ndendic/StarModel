"""
Migration Tracker for StarModel Screaming Architecture

Tracks migration progress and validates completeness of the transition
from framework-centric to domain-centric organization.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
from datetime import datetime

@dataclass
class FileMapping:
    """Represents a single file migration mapping"""
    old_path: str
    new_path: str
    migrated: bool = False
    tested: bool = False
    migration_date: Optional[str] = None
    notes: str = ""

@dataclass
class MigrationStatus:
    """Overall migration status summary"""
    total_files: int
    migrated: int
    tested: int
    remaining: int
    progress_percent: float

class MigrationTracker:
    """
    Tracks and manages the complete migration from current structure
    to screaming architecture organization.
    """
    
    def __init__(self, status_file: str = "tools/migration/migration_status.json"):
        self.status_file = Path(status_file)
        self.mappings: List[FileMapping] = []
        self._load_migration_plan()
        self._load_status()
    
    def _load_migration_plan(self):
        """Load the complete file migration mapping"""
        self.mappings = [
            # ===== CORE ENTITY SYSTEM =====
            FileMapping(
                "src/starmodel/core/entity.py", 
                "framework/entities/lifecycle/entity.py",
                notes="Core Entity class - heart of StarModel"
            ),
            FileMapping(
                "src/starmodel/core/events.py", 
                "framework/events/commands/event.py",
                notes="@event decorator and command definitions"
            ),
            FileMapping(
                "src/starmodel/core/signals.py", 
                "framework/reactivity/signals/signal_system.py",
                notes="Reactive signals for UI binding"
            ),
            FileMapping(
                "src/starmodel/core/mixins/entity_mixin.py", 
                "framework/entities/behavior/mixins.py",
                notes="Entity behavior mixins"
            ),
            FileMapping(
                "src/starmodel/core/mixins/persistence_mixin.py", 
                "framework/persistence/repositories/mixins.py",
                notes="Persistence mixin functionality"
            ),
            
            # ===== APPLICATION LAYER =====
            FileMapping(
                "src/starmodel/app/dispatcher.py", 
                "framework/events/dispatching/dispatcher.py",
                notes="Command dispatcher - central coordination"
            ),
            FileMapping(
                "src/starmodel/app/bus.py", 
                "framework/events/streaming/event_bus.py",
                notes="Event bus for pub/sub messaging"
            ),
            FileMapping(
                "src/starmodel/app/uow.py", 
                "framework/persistence/transactions/unit_of_work.py",
                notes="Unit of Work pattern for transactions"
            ),
            FileMapping(
                "src/starmodel/app/configurator.py", 
                "framework/infrastructure/deployment/configurator.py",
                notes="Application configuration and setup"
            ),
            
            # ===== PERSISTENCE LAYER =====
            FileMapping(
                "src/starmodel/persistence/memory.py", 
                "framework/persistence/backends/memory.py",
                notes="Memory-based persistence backend"
            ),
            FileMapping(
                "src/starmodel/persistence/sql.py", 
                "framework/persistence/backends/sql.py",
                notes="SQL persistence backend"
            ),
            FileMapping(
                "src/starmodel/persistence/base.py", 
                "framework/persistence/repositories/base.py",
                notes="Base persistence interfaces and patterns"
            ),
            FileMapping(
                "src/starmodel/persistence/datastar.py", 
                "framework/realtime/protocols/datastar.py",
                notes="Datastar SSE protocol implementation"
            ),
            
            # ===== WEB INFRASTRUCTURE =====
            FileMapping(
                "src/starmodel/adapters/fasthtml.py", 
                "framework/infrastructure/web/fasthtml_adapter.py",
                notes="FastHTML web framework adapter"
            ),
            FileMapping(
                "src/starmodel/web/", 
                "framework/infrastructure/web/",
                notes="Web framework integration utilities"
            ),
            
            # ===== CLI TOOLS =====
            FileMapping(
                "src/starmodel/cli/cli.py", 
                "tools/cli/starmodel_cli.py",
                notes="StarModel CLI commands"
            ),
            FileMapping(
                "src/starmodel/cli/templates/", 
                "tools/scaffolding/templates/",
                notes="Project scaffolding templates"
            ),
            
            # ===== DEMO APPLICATIONS =====
            FileMapping(
                "app/entities/", 
                "examples/full-demo/entities/",
                notes="Demo entity definitions"
            ),
            FileMapping(
                "app/pages/", 
                "examples/full-demo/pages/",
                notes="Demo page implementations"
            ),
            FileMapping(
                "app/main.py", 
                "examples/full-demo/main.py",
                notes="Full demo application entry point"
            ),
            
            # ===== PACKAGE STRUCTURE =====
            FileMapping(
                "src/starmodel/__init__.py", 
                "framework/__init__.py",
                notes="Main package initialization with screaming architecture"
            ),
        ]
    
    def _load_status(self):
        """Load migration status from file if it exists"""
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r') as f:
                    data = json.load(f)
                    
                # Update mapping status from saved data
                for saved_mapping in data.get('mappings', []):
                    for mapping in self.mappings:
                        if mapping.old_path == saved_mapping['old_path']:
                            mapping.migrated = saved_mapping.get('migrated', False)
                            mapping.tested = saved_mapping.get('tested', False)
                            mapping.migration_date = saved_mapping.get('migration_date')
                            mapping.notes = saved_mapping.get('notes', mapping.notes)
                            break
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Could not load migration status: {e}")
    
    def _save_status(self):
        """Save current migration status to file"""
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'last_updated': datetime.now().isoformat(),
            'mappings': [
                {
                    'old_path': m.old_path,
                    'new_path': m.new_path,
                    'migrated': m.migrated,
                    'tested': m.tested,
                    'migration_date': m.migration_date,
                    'notes': m.notes
                }
                for m in self.mappings
            ]
        }
        
        with open(self.status_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def mark_migrated(self, old_path: str, notes: str = "") -> bool:
        """Mark a file as successfully migrated"""
        for mapping in self.mappings:
            if mapping.old_path == old_path:
                mapping.migrated = True
                mapping.migration_date = datetime.now().isoformat()
                if notes:
                    mapping.notes += f" | {notes}"
                self._save_status()
                print(f"✅ Marked as migrated: {old_path} → {mapping.new_path}")
                return True
        
        print(f"❌ File not found in migration plan: {old_path}")
        return False
    
    def mark_tested(self, old_path: str) -> bool:
        """Mark a migrated file as tested"""
        for mapping in self.mappings:
            if mapping.old_path == old_path and mapping.migrated:
                mapping.tested = True
                self._save_status()
                print(f"✅ Marked as tested: {old_path}")
                return True
        
        print(f"❌ File not migrated or not found: {old_path}")
        return False
    
    def get_migration_status(self) -> MigrationStatus:
        """Get overall migration status"""
        total = len(self.mappings)
        migrated = sum(1 for m in self.mappings if m.migrated)
        tested = sum(1 for m in self.mappings if m.tested)
        remaining = total - migrated
        progress = (migrated / total * 100) if total > 0 else 0
        
        return MigrationStatus(
            total_files=total,
            migrated=migrated,
            tested=tested,
            remaining=remaining,
            progress_percent=round(progress, 1)
        )
    
    def get_next_files_to_migrate(self, count: int = 5) -> List[FileMapping]:
        """Get the next files that should be migrated"""
        unmigrated = [m for m in self.mappings if not m.migrated]
        return unmigrated[:count]
    
    def get_files_needing_tests(self) -> List[FileMapping]:
        """Get migrated files that still need testing"""
        return [m for m in self.mappings if m.migrated and not m.tested]
    
    def print_status_report(self):
        """Print a comprehensive status report"""
        status = self.get_migration_status()
        
        print("\n" + "="*60)
        print("🚀 STARMODEL SCREAMING ARCHITECTURE MIGRATION STATUS")
        print("="*60)
        
        print(f"\n📊 Overall Progress: {status.progress_percent}%")
        print(f"   Total files: {status.total_files}")
        print(f"   Migrated: {status.migrated}")
        print(f"   Tested: {status.tested}")
        print(f"   Remaining: {status.remaining}")
        
        if status.remaining > 0:
            print(f"\n📝 Next files to migrate:")
            next_files = self.get_next_files_to_migrate(3)
            for i, mapping in enumerate(next_files, 1):
                print(f"   {i}. {mapping.old_path}")
                print(f"      → {mapping.new_path}")
                print(f"      📋 {mapping.notes}")
        
        untested = self.get_files_needing_tests()
        if untested:
            print(f"\n🧪 Files needing tests ({len(untested)}):")
            for mapping in untested[:3]:
                print(f"   • {mapping.new_path}")
        
        if status.remaining == 0:
            print("\n🎉 Migration complete! All files have been migrated.")
            if status.tested == status.total_files:
                print("✅ All files have been tested.")
            else:
                print(f"⚠️  {status.total_files - status.tested} files still need testing.")
    
    def validate_migration(self) -> Tuple[bool, List[str]]:
        """Validate that migration is complete and correct"""
        issues = []
        
        # Check all files are migrated
        unmigrated = [m.old_path for m in self.mappings if not m.migrated]
        if unmigrated:
            issues.append(f"Unmigrated files: {', '.join(unmigrated)}")
        
        # Check all files are tested
        untested = [m.new_path for m in self.mappings if m.migrated and not m.tested]
        if untested:
            issues.append(f"Untested files: {', '.join(untested[:5])}")
        
        # Check new files exist
        for mapping in self.mappings:
            if mapping.migrated:
                new_file = Path(mapping.new_path)
                if not new_file.exists():
                    issues.append(f"Missing migrated file: {mapping.new_path}")
        
        return len(issues) == 0, issues

def main():
    """CLI interface for migration tracker"""
    import sys
    
    tracker = MigrationTracker()
    
    if len(sys.argv) == 1:
        # No arguments - show status
        tracker.print_status_report()
    
    elif sys.argv[1] == "status":
        tracker.print_status_report()
    
    elif sys.argv[1] == "migrated" and len(sys.argv) > 2:
        old_path = sys.argv[2]
        notes = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        tracker.mark_migrated(old_path, notes)
    
    elif sys.argv[1] == "tested" and len(sys.argv) > 2:
        old_path = sys.argv[2]
        tracker.mark_tested(old_path)
    
    elif sys.argv[1] == "validate":
        is_valid, issues = tracker.validate_migration()
        if is_valid:
            print("✅ Migration validation passed!")
        else:
            print("❌ Migration validation failed:")
            for issue in issues:
                print(f"   • {issue}")
            sys.exit(1)
    
    else:
        print("Usage:")
        print("  python tools/migration/tracker.py status")
        print("  python tools/migration/tracker.py migrated <old_path> [notes]")
        print("  python tools/migration/tracker.py tested <old_path>")
        print("  python tools/migration/tracker.py validate")

if __name__ == "__main__":
    main()