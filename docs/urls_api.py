from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_api import BookViewSet, ChapterViewSet

router = DefaultRouter()
router.register(r'books', BookViewSet)
router.register(r'chapters', ChapterViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
