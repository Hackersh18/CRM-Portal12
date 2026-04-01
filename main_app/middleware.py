from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin


class LoginCheckMiddleware(MiddlewareMixin):
    """Send admins and counsellors to their own app; require login elsewhere."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        if getattr(view_func, "allow_without_login", False):
            return None

        module = view_func.__module__
        user = request.user

        if user.is_authenticated:
            ut = str(getattr(user, "user_type", ""))
            if ut == "1" and module == "main_app.counsellor_views":
                return redirect(reverse("admin_home"))
            if ut == "2" and module == "main_app.admin_views":
                return redirect(reverse("counsellor_home"))
            if ut not in ("1", "2"):
                return redirect(reverse("login_page"))
            return None

        login_path = reverse('login_page')
        user_login_path = reverse('user_login')
        if (
            request.path == login_path
            or request.path == user_login_path
            or module == 'django.contrib.auth.views'
        ):
            return None
        return redirect(login_path)
