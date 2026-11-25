from .models import Notification


def notification_context(request):
    """
    Context processor to supply recent notifications and unread count
    globally across all authenticated templates.
    """
    if getattr(request, 'user', None) and request.user.is_authenticated:
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        recent_notifications = Notification.objects.filter(
            recipient=request.user
        ).select_related('related_project', 'related_task')[:5]
        return {
            'unread_notifications_count': unread_count,
            'recent_notifications': recent_notifications,
        }
    return {
        'unread_notifications_count': 0,
        'recent_notifications': [],
    }
