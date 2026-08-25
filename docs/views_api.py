from rest_framework import viewsets, permissions
from .models import Book, Chapter
from .serializers import BookSerializer, ChapterSerializer
from courses.helpers import is_admin
from courses.permissions import IsInstructorOrAdmin, CanManageBook

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    filterset_fields = ['author', 'is_free_book']
    search_fields = ['title', 'description']
    ordering_fields = ['order', 'title']
    
    def get_permissions(self):
        if self.action in ['create']:
            return [permissions.IsAuthenticated(), IsInstructorOrAdmin()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsInstructorOrAdmin(), CanManageBook()]
        return [permissions.AllowAny()]
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    def perform_update(self, serializer):
        if is_admin(self.request.user):
            serializer.save()
        else:
            serializer.save(author=self.request.user)

class ChapterViewSet(viewsets.ModelViewSet):
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer
    filterset_fields = ['book']
    ordering_fields = ['order', 'title']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsInstructorOrAdmin()]
        return [permissions.IsAuthenticatedOrReadOnly()]
