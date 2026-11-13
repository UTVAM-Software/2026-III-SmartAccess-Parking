"""Prevent authenticated and administrative HTML pages from being cached."""

from django.utils.cache import patch_cache_control


class NoStoreHTMLMiddleware:
    """Make the browser revalidate HTML instead of restoring stale private pages."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.get("Content-Type", "").startswith("text/html"):
            patch_cache_control(
                response,
                private=True,
                no_store=True,
                no_cache=True,
                must_revalidate=True,
                max_age=0,
            )
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"
        return response
