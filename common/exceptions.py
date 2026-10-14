from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data
    response.data = {
        "error": {
            "status_code": response.status_code,
            "code": getattr(exc, "default_code", "error"),
            "details": detail,
        }
    }
    return response

