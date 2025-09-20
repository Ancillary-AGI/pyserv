#!/usr/bin/env python3
"""
PyDance Router Demo
Demonstrates advanced routing features including redirects, views, and fallbacks
"""

import sys
import os
from pathlib import Path

# Set up the path to include src
examples_dir = Path(__file__).parent
project_root = examples_dir.parent
src_dir = project_root / 'src'
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

def print_header(title: str, description: str = ""):
    """Print a formatted header for examples."""
    print(f"🚀 {title}")
    if description:
        print(description)
    print("=" * 50)
    print()

def print_success(message: str):
    """Print a success message."""
    print(f"✅ {message}")

def handle_example_error(func):
    """Decorator to handle errors in examples gracefully."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"❌ Error running example: {e}")
            import traceback
            traceback.print_exc()
            return None
    return wrapper

from pydance.core.routing import Router, RouteType
from pydance.views.base import TemplateView, ListView, DetailView, FormView
from pydance.core.http.response import Response


def home_handler(request):
    """Simple home page handler"""
    return Response("<h1>Welcome to PyDance!</h1><p>This is the home page.</p>", content_type="text/html")


def about_handler(request):
    """About page handler"""
    return Response("<h1>About PyDance</h1><p>A comprehensive web framework.</p>", content_type="text/html")


def user_profile_handler(request, user_id):
    """User profile handler with parameter"""
    return Response(f"<h1>User Profile</h1><p>User ID: {user_id}</p>", content_type="text/html")


def api_handler(request):
    """API endpoint handler"""
    return Response.json({"message": "API endpoint", "status": "success"})


class HomeView(TemplateView):
    """Class-based view example"""
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Welcome to PyDance'
        context['message'] = 'This is a class-based view!'
        return context


class UserListView(ListView):
    """List view example"""
    template_name = "users.html"
    context_object_name = "users"

    def get_queryset(self):
        # Mock data - in real app this would come from database
        return [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
            {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
        ]


class UserDetailView(DetailView):
    """Detail view example"""
    template_name = "user_detail.html"

    def get_object(self):
        user_id = self.kwargs.get('user_id')
        # Mock data - in real app this would come from database
        users = {
            "1": {"id": 1, "name": "Alice", "email": "alice@example.com"},
            "2": {"id": 2, "name": "Bob", "email": "bob@example.com"},
            "3": {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
        }
        return users.get(user_id)


def create_demo_router():
    """Create a demo router with all advanced features"""

    router = Router()

    # Basic routes
    router.add_route("/", home_handler, name="home")
    router.add_route("/about", about_handler, name="about")

    # Routes with parameters and constraints
    router.add_route(
        "/user/{user_id}",
        user_profile_handler,
        constraints={"user_id": r"\d+"},  # Only digits
        name="user_profile"
    )

    # API routes with scheme constraints
    router.add_route(
        "/api/data",
        api_handler,
        methods=["GET", "POST"],
        schemes=["https"],  # Only HTTPS
        name="api_data"
    )

    # Redirect routes
    router.add_permanent_redirect("/old-home", "/")
    router.add_temporary_redirect("/temp-about", "/about")

    # Custom redirect with parameters
    def custom_redirect_handler(request, **kwargs):
        user_id = kwargs.get('user_id', '1')
        return Response.redirect(f"/user/{user_id}", 302)

    router.add_route(
        "/redirect-user/{user_id}",
        custom_redirect_handler,
        route_type=RouteType.REDIRECT,
        name="redirect_user"
    )

    # View-based routes
    router.add_view_route("/home-view", HomeView, name="home_view")
    router.add_view_route("/users", UserListView, name="user_list")
    router.add_view_route("/user-detail/{user_id}", UserDetailView, name="user_detail")

    # Fallback route
    def not_found_handler(request):
        return Response("<h1>404 - Page Not Found</h1>", status=404, content_type="text/html")

    router.add_fallback_route("/404", not_found_handler)

    # Route groups
    api_group = router.group("/api/v1", name_prefix="api_v1")

    def api_users_handler(request):
        return Response.json({"users": ["Alice", "Bob", "Charlie"]})

    def api_user_handler(request, user_id):
        return Response.json({"user_id": user_id, "name": f"User {user_id}"})

    api_group.add_route("/users", api_users_handler, name="users")
    api_group.add_route("/user/{user_id}", api_user_handler, name="user")

    return router


def demo_router_features():
    """Demonstrate router features"""

    print("🚀 PyDance Router Demo")
    print("=" * 50)

    router = create_demo_router()

    # Test basic routing
    print("\n📍 Basic Routing Tests:")
    test_cases = [
        ("/", "GET"),
        ("/about", "GET"),
        ("/user/123", "GET"),
        ("/api/data", "GET"),
        ("/nonexistent", "GET"),
    ]

    for path, method in test_cases:
        route, params = router.find_route(path, method)
        if route:
            print(f"  ✅ {method} {path} -> {route.handler.__name__} with params: {params}")
        else:
            print(f"  ❌ {method} {path} -> No route found")

    # Test redirects
    print("\n🔄 Redirect Tests:")
    redirect_cases = [
        ("/old-home", "GET"),
        ("/temp-about", "GET"),
        ("/redirect-user/456", "GET"),
    ]

    for path, method in redirect_cases:
        route, params = router.find_route(path, method)
        if route and route.route_type == RouteType.REDIRECT:
            redirect_url = route.get_redirect_url(params)
            print(f"  ✅ {method} {path} -> Redirects to: {redirect_url}")
        else:
            print(f"  ❌ {method} {path} -> Not a redirect")

    # Test URL generation
    print("\n🔗 URL Generation Tests:")
    url_tests = [
        ("home", {}),
        ("user_profile", {"user_id": "789"}),
        ("api_v1_users", {}),
        ("api_v1_user", {"user_id": "999"}),
    ]

    for route_name, params in url_tests:
        url = router.url_for(route_name, **params)
        if url:
            print(f"  ✅ {route_name} with {params} -> {url}")
        else:
            print(f"  ❌ {route_name} -> URL generation failed")

    # Test constraints
    print("\n🔒 Constraint Tests:")
    constraint_tests = [
        ("/user/123", "GET"),  # Should work (digits only)
        ("/user/abc", "GET"),  # Should fail (letters not allowed)
    ]

    for path, method in constraint_tests:
        route, params = router.find_route(path, method)
        if route:
            print(f"  ✅ {method} {path} -> Matched with params: {params}")
        else:
            print(f"  ❌ {method} {path} -> Constraint violation")

    # Test route groups
    print("\n📁 Route Group Tests:")
    group_tests = [
        ("/api/v1/users", "GET"),
        ("/api/v1/user/777", "GET"),
    ]

    for path, method in group_tests:
        route, params = router.find_route(path, method)
        if route:
            print(f"  ✅ {method} {path} -> {route.handler.__name__} with params: {params}")
        else:
            print(f"  ❌ {method} {path} -> No route in group")

    print("\n🎉 Router demo completed!")
    print("\nFeatures demonstrated:")
    print("  • Basic routing with parameters")
    print("  • Route constraints and validation")
    print("  • Redirect routes (permanent and temporary)")
    print("  • View-based routes with class-based views")
    print("  • Route groups with prefixes")
    print("  • URL generation from route names")
    print("  • Fallback routes for 404 handling")


@handle_example_error
def main():
    """Main function for the router demo."""
    print_header(
        "PyDance Router Demo",
        "Demonstrates advanced routing features including redirects, views, and fallbacks"
    )

    demo_router_features()

    print_success("Router demo completed successfully!")
    print("\nFeatures demonstrated:")
    print("  • Basic routing with parameters")
    print("  • Route constraints and validation")
    print("  • Redirect routes (permanent and temporary)")
    print("  • View-based routes with class-based views")
    print("  • Route groups with prefixes")
    print("  • URL generation from route names")
    print("  • Fallback routes for 404 handling")


if __name__ == "__main__":
    main()
