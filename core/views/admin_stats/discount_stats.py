from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.db.models.functions import TruncDate
from django.db.models import Count
from django.shortcuts import render
from core.models import DiscountActivation

__all__ = [
    'discount_stats_view',
]

@staff_member_required
def discount_stats_view(request):
    qs = DiscountActivation.objects.all()
    qs = qs.annotate(date=TruncDate('activated_at')).values('date').annotate(count=Count('id')).order_by('date')
    labels = [str(item['date']) for item in qs]
    data = [item['count'] for item in qs]
    chart_data = {'labels': labels, 'data': data}
    return render(request, 'core/discount_stats.html', {'chart_data': chart_data})
