from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from .models import (
    Course, Lesson, Enrollment, Notification, 
    CommunityVoice, Profile, NewsletterSubscriber
)
from .serializers import (
    CourseSerializer, LessonSerializer, EnrollmentSerializer,
    NotificationSerializer, CommunityVoiceSerializer,
    ProfileSerializer, NewsletterSubscriberSerializer, UserSerializer
)
from .helpers import is_instructor, is_admin
from .permissions import IsInstructorOrAdmin, IsAdminOnly, CanManageCourse

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    filterset_fields = ['instructor']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'title']
    
    def get_permissions(self):
        if self.action in ['create']:
            return [permissions.IsAuthenticated(), IsInstructorOrAdmin()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsInstructorOrAdmin(), CanManageCourse()]
        return [permissions.AllowAny()]
    
    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)
    
    def perform_update(self, serializer):
        if is_admin(self.request.user):
            serializer.save()
        else:
            serializer.save(instructor=self.request.user)

class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    filterset_fields = ['course']
    ordering_fields = ['order', 'title']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsInstructorOrAdmin()]
        return [permissions.IsAuthenticatedOrReadOnly()]

class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    filterset_fields = ['student', 'course']
    
    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and (user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'admin')):
            return Enrollment.objects.all()
        if user.is_authenticated:
            return Enrollment.objects.filter(student=user)
        return Enrollment.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(student=self.request.user)
    
    @action(detail=True, methods=['post'])
    def complete_lesson(self, request, pk=None):
        enrollment = self.get_object()
        lesson_id = request.data.get('lesson_id')
        if not lesson_id:
            return Response({'error': 'lesson_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        lesson = get_object_or_404(Lesson, id=lesson_id, course=enrollment.course)
        enrollment.completed_lessons.add(lesson)
        return Response({'status': 'lesson marked as complete'})

class CommunityVoiceViewSet(viewsets.ModelViewSet):
    queryset = CommunityVoice.objects.filter(is_approved=True)
    serializer_class = CommunityVoiceSerializer
    
    def get_permissions(self):
        if self.action in ['create']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and (user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'admin')):
            return CommunityVoice.objects.all()
        return CommunityVoice.objects.filter(is_approved=True)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        if not is_admin(request.user):
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        voice = self.get_object()
        voice.is_approved = True
        voice.save()
        return Response({'status': 'voice approved'})

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    queryset = Notification.objects.all()
    
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return Notification.objects.filter(user=user)
        return Notification.objects.none()
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})

class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Profile.objects.all()
    
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and is_admin(user):
            return Profile.objects.all()
        if user.is_authenticated:
            return Profile.objects.filter(user=user)
        return Profile.objects.none()
    
    def get_object(self):
        return self.request.user.profile
    
    def perform_update(self, serializer):
        instance = serializer.instance
        if not is_admin(self.request.user):
            validated_data = dict(serializer.validated_data)
            validated_data.pop('role', None)
            serializer.save(**validated_data)
        else:
            serializer.save()

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and (user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'admin')):
            return User.objects.all()
        return User.objects.filter(id=user.id)

class NewsletterSubscriberViewSet(viewsets.ModelViewSet):
    queryset = NewsletterSubscriber.objects.all()
    serializer_class = NewsletterSubscriberSerializer
    
    def get_permissions(self):
        if self.action in ['create']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), permissions.DjangoModelPermissions()]
