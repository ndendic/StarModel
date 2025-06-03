import importlib
import pkgutil

from fasthtml.core import APIRouter, FastHTML

def collect_rt_instances(package_name) -> list[APIRouter]:
    rt_list = []

    # Import the modules package
    try:
        modules_package = importlib.import_module(package_name)
    except ImportError as e:
        print(f"Failed to import {package_name}: {e}")
        return rt_list

    for loader, module_name, is_pkg in pkgutil.walk_packages(
        modules_package.__path__, modules_package.__name__ + "."
    ):
        try:
            # Try to import the module
            module = importlib.import_module(module_name)

            # Check for direct rt attribute
            if hasattr(module, "rt"):
                rt_attr = module.rt
                rt_list.append(rt_attr)
                print(f"Imported routes from {module_name}")

            # If it's a package and has 'routes' in its name, walk through all its modules
            elif is_pkg and 'routes' in module_name:
                package_path = module.__path__
                for sub_loader, sub_module_name, _ in pkgutil.walk_packages(
                    package_path, module_name + "."
                ):
                    try:
                        sub_module = importlib.import_module(sub_module_name)
                        if hasattr(sub_module, "rt"):
                            rt_attr = sub_module.rt
                            rt_list.append(rt_attr)
                    except Exception as e:
                        print(f"Failed to import {sub_module_name}: {e}")

        except Exception as e:
            print(f"Failed to import {module_name}: {e}")

    return rt_list

def add_routes(app: FastHTML, from_package: str = "pages") -> FastHTML:
    routes = collect_rt_instances(from_package)
    for rt in routes:
        rt.to_app(app)
    return app
