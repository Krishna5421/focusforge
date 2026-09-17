import logging

from django.http import JsonResponse
from django.shortcuts import render


logger = logging.getLogger('django.request')


def _expects_json(request):
    return (
        request.path.startswith('/api/')
        or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('Accept', '')
    )


def _error_response(request, status, title, message):
    if _expects_json(request):
        return JsonResponse({'error': message}, status=status)
    return render(request, 'errors/error.html', {
        'status_code': status,
        'title': title,
        'message': message,
    }, status=status)


def bad_request(request, exception=None):
    return _error_response(request, 400, 'Invalid request', 'We could not process that request. Please check your details and try again.')


def permission_denied(request, exception=None):
    return _error_response(request, 403, 'Access denied', 'You do not have permission to view this page.')


def page_not_found(request, exception=None):
    return _error_response(request, 404, 'Page not found', 'The page you requested does not exist or may have moved.')


def server_error(request):
    logger.error('Unhandled server error on %s', request.path)
    return _error_response(request, 500, 'Something went wrong', 'We could not complete that action. Please try again in a moment.')
