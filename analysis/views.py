from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import Event
import json
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Avg
from django.utils import timezone

# 테스트용 ping
@api_view(['GET'])
def ping(request):
    return Response({"message": "pong"})

# def video_list(request):
#     videos = Video.objects.all()

#     region = request.GET.get('region')
#     keyword = request.GET.get('keyword')

#     if region:
#         videos = videos.filter(region=region)

#     if keyword:
#         videos = videos.filter(filename__icontains=keyword)

#     sort = request.GET.get('sort', 'date')
#     if sort == 'date':
#         videos = videos.order_by('-date')
#     elif sort == 'region':
#         videos = videos.order_by('region')

#     page = int(request.GET.get('page', 1))
#     size = int(request.GET.get('size', 10))

#     paginator = Paginator(videos, size)
#     page_obj = paginator.get_page(page)

#     data = []
#     for v in page_obj:
#         data.append({
#             "id": v.id,
#             "filename": v.filename,
#             "thumbnail": v.thumbnail.url if v.thumbnail else None,
#             "date": v.date,
#             "region": v.region,
#             "fish_count": v.fish_count,
#             "total_count": v.total_count,
#             "severity": "HIGH" if v.fish_count >= 10 else "LOW"
#         })

#     return JsonResponse({
#         "videos": data,
#         "total_pages": paginator.num_pages
#     })


# @csrf_exempt
# def video_delete(request):
#     if request.method == "DELETE":
#         body = json.loads(request.body)
#         ids = body.get("video_ids", [])

#         Video.objects.filter(id__in=ids).delete()
        
#         SystemLog.objects.create(
#             event_type="DELETE_VIDEO",
#             message="영상 삭제됨",
#             user_id=1
#         )

#         return JsonResponse({"success": True})

# def video_detail(request, video_id):
#     try:
#         v = Video.objects.get(id=video_id)
#     except Video.DoesNotExist:
#         return JsonResponse({"message": "존재하지 않는 영상입니다."}, status=404)

#     region_avg = Video.objects.filter(region=v.region).aggregate(
#         avg=Avg("fish_count")
#     )["avg"] or 0

#     year_avg = Video.objects.filter(date__year=timezone.now().year).aggregate(
#         avg=Avg("fish_count")
#     )["avg"] or 0

#     return JsonResponse({
#         "id": v.id,
#         "filename": v.filename,
#         "date": str(v.date),
#         "uploadTime": str(v.date),
#         "region": v.region,
#         "location": getattr(v, "location", ""),
#         "gps": getattr(v, "gps", ""),
#         "ganjunchiCount": v.fish_count,
#         "totalCount": v.total_count,
#         "weather": getattr(v, "weather", ""),
#         "duration": getattr(v, "duration", ""),
#         "detectionRanges": [],
#         "regionAvg": int(region_avg),
#         "yearAvg": int(year_avg),
#         "uploader": getattr(v, "uploader", "")
#     })

@api_view(['GET'])
def log_list(request):
    logs = Event.objects.all().order_by('-created_at')
    items = []

    for log in logs:
        created_at = timezone.localtime(log.created_at)

        if log.user is None:
            username = "시스템"
        else:
            username = getattr(log.user, "username", None) or str(log.user)

        items.append(
            {
                "id": log.id,
                "dateTime": created_at.strftime("%Y-%m-%d %H:%M"),
                "eventType": log.type,
                "detail": log.detail,
                "user": username,
            }
        )

    return Response(
        {
            "items": items
        },
        status=status.HTTP_200_OK,
    )
