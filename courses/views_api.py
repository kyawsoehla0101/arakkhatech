from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q
from .models import (
    Course, Lesson, Enrollment, Notification,
    CommunityVoice, Profile, NewsletterSubscriber
)
from .serializers import (
    CourseSerializer, LessonSerializer, EnrollmentSerializer,
    NotificationSerializer, CommunityVoiceSerializer,
    ProfileSerializer, NewsletterSubscriberSerializer,
    UserSerializer, UserRegisterSerializer, UserAdminCreateSerializer,
    UserAdminUpdateSerializer, UserChangePasswordSerializer,
    InstructorEnrollStudentSerializer
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
        if not user.is_authenticated:
            return Enrollment.objects.none()
        if is_admin(user):
            return Enrollment.objects.all()
        if is_instructor(user):
            return Enrollment.objects.filter(
                Q(student=user) | Q(course__instructor=user)
            ).distinct()
        return Enrollment.objects.filter(student=user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    def perform_destroy(self, instance):
        user = self.request.user
        if not is_admin(user) and instance.course.instructor_id != getattr(user, 'pk', None):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("ဤစာရင်းကို ဖျက်ခွင့်မရှိပါ")
        super().perform_destroy(instance)

    @action(detail=True, methods=['post'])
    def complete_lesson(self, request, pk=None):
        enrollment = self.get_object()
        lesson_id = request.data.get('lesson_id')
        if not lesson_id:
            return Response({'error': 'lesson_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        lesson = get_object_or_404(Lesson, id=lesson_id, course=enrollment.course)
        enrollment.completed_lessons.add(lesson)
        return Response({'status': 'lesson marked as complete'})

    @action(detail=False, methods=['post'])
    def enroll_user(self, request):
        """
        Instructor / Admin သည် username_or_email နှင့် course_id ဖြင့်
        ကျောင်းသားအား သင်တန်းသို့ စာရင်းသွင်းပေးနိုင်သည်
        """
        if not is_admin(request.user) and not is_instructor(request.user):
            return Response({'error': 'လုပ်ပိုင်ခွင့်မရှိပါ'}, status=status.HTTP_403_FORBIDDEN)
        serializer = InstructorEnrollStudentSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        student = serializer.validated_data['_student']
        course = serializer.validated_data['_course']
        enrollment = Enrollment.objects.create(student=student, course=course)
        try:
            Notification.objects.create(
                user=student,
                title='သင်တန်းသို့ စာရင်းသွင်းခြင်း အောင်မြင်သည်',
                message=f"{course.title} သင်တန်းသို့ စာရင်းသွင်းပြီးပါပြီ။ အခုသင်လို့ရပါပြီ။",
                notification_type='info'
            )
        except Exception:
            pass
        output = EnrollmentSerializer(enrollment, context={'request': request})
        return Response({
            'status': 'success',
            'message': 'စာရင်းသွင်းခြင်း အောင်မြင်ပါသည်',
            'enrollment': output.data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def manage(self, request):
        """
        Instructor သည် သူ့ရဲ့ course တွေရဲ့ enrollment အားလုံး၊
        Admin သည် စနစ်ရဲ့ enrollment အားလုံးကို ကြည့်နိုင်သည်
        """
        if not is_admin(request.user) and not is_instructor(request.user):
            return Response({'error': 'လုပ်ပိုင်ခွင့်မရှိပါ'}, status=status.HTTP_403_FORBIDDEN)
        qs = self.get_queryset()
        if not is_admin(request.user):
            qs = qs.filter(course__instructor=request.user)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = EnrollmentSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = EnrollmentSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)


class CommunityVoiceViewSet(viewsets.ModelViewSet):
    queryset = CommunityVoice.objects.filter(is_approved=True)
    serializer_class = CommunityVoiceSerializer

    def get_permissions(self):
        if self.action in ['create']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and is_admin(user):
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
        pk = self.kwargs.get('pk')
        user = self.request.user
        if is_admin(user) and pk not in (None, 'me'):
            return get_object_or_404(Profile, pk=pk)
        return self.request.user.profile

    def perform_update(self, serializer):
        instance = serializer.instance
        if not is_admin(self.request.user):
            validated_data = dict(serializer.validated_data)
            validated_data.pop('role', None)
            serializer.save(**validated_data)
        else:
            serializer.save()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'username', 'email']

    def get_serializer_class(self):
        if self.action == 'register':
            return UserRegisterSerializer
        if self.action == 'create':
            return UserAdminCreateSerializer
        if self.action in ['update', 'partial_update']:
            return UserAdminUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == 'register':
            return [permissions.AllowAny()]
        if self.action in ['me', 'change_password']:
            return [permissions.IsAuthenticated()]
        if self.action in ['create', 'destroy', 'change_role', 'deactivate', 'activate', 'list']:
            return [permissions.IsAuthenticated(), IsAdminOnly()]
        if self.action in ['update', 'partial_update', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return User.objects.none()
        if is_admin(user):
            role = self.request.query_params.get('role')
            qs = User.objects.all()
            if role:
                qs = qs.filter(profile__role=role)
            return qs
        return User.objects.filter(id=user.id)

    def get_object(self):
        pk = self.kwargs.get('pk')
        if pk == 'me' or pk is None:
            return self.request.user
        if not is_admin(self.request.user) and str(pk) != str(self.request.user.pk):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("သတ်မှတ်ထားသော User အကြောင်း အသေးစိတ်ကို ကြည့်ရှုခွင့်မရှိပါ")
        return super().get_object()

    @action(detail=False, methods=['get'])
    def me(self, request):
        """လက်ရှိ login ဝင်ထားသူ့ရဲ့ အချက်အလက် အကျဉ်းချက် ကို ပြန်ပေးသည်"""
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def register(self, request):
        """ကျောင်းသား(student) အဖြစ် အကောင့်အသစ် ဖွင့်နိုင်သည် (သာမန်လူပေါင်းသုံးပစ္စည်း)"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            'status': 'success',
            'message': 'အကောင့်အသစ် ဖွင့်ခြင်း အောင်မြင်ပါသည်',
            'user': UserSerializer(user, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """လက်ရှိ user သည် ကိုယ်ပိုင် password အသစ်ပြောင်းလဲနိုင်သည်"""
        serializer = UserChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({
                'status': 'error',
                'message': 'လက်ရှိ လျှို့ဝှက်နံပါတ် မှားယွင်းနေပါသည်'
            }, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        try:
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)
        except Exception:
            pass
        return Response({
            'status': 'success',
            'message': 'လျှို့ဝှက်နံပါတ် ပြောင်းလဲခြင်း အောင်မြင်ပါသည်'
        })

    @action(detail=True, methods=['post'])
    def change_role(self, request, pk=None):
        """Admin သည် user ၏ role ကို ပြောင်းလဲနိုင်သည် (student / instructor / admin)"""
        if not is_admin(request.user):
            return Response({'error': 'လုပ်ပိုင်ခွင့်မရှိပါ'}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object()
        role = str(request.data.get('role', '')).strip().lower()
        allowed_roles = {'student', 'instructor', 'admin'}
        if role not in allowed_roles:
            return Response({
                'status': 'error',
                'message': 'role မမှန်ကန်ပါ (student / instructor / admin) မှရွေးချယ်ပါ'
            }, status=status.HTTP_400_BAD_REQUEST)
        profile, _ = Profile.objects.get_or_create(user=user, defaults={'role': role})
        if profile.role != role:
            profile.role = role
            profile.save(update_fields=['role'])
        return Response({
            'status': 'success',
            'message': 'Role ပြောင်းလဲခြင်း အောင်မြင်ပါသည်',
            'user': UserSerializer(user, context={'request': request}).data
        })

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Admin သည် user အကောင့်ကို deactivate (ပိတ်ပစ်) နိုင်သည်"""
        if not is_admin(request.user):
            return Response({'error': 'လုပ်ပိုင်ခွင့်မရှိပါ'}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object()
        if user.pk == request.user.pk:
            return Response({
                'status': 'error',
                'message': 'ကိုယ်ပိုင်အကောင့်ကို အလိုအလျောက် ပိတ်နိုင်မည် မဟုတ်ပါ'
            }, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response({
            'status': 'success',
            'message': 'အကောင့်ကို ပိတ်ပစ်ပြီးပါပြီ',
            'user': UserSerializer(user, context={'request': request}).data
        })

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Admin သည် deactivated အကောင့်ကို ပြန်လည် ဖွင့်ပေးနိုင်သည်"""
        if not is_admin(request.user):
            return Response({'error': 'လုပ်ပိုင်ခွင့်မရှိပါ'}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=['is_active'])
        return Response({
            'status': 'success',
            'message': 'အကောင့်ကို ပြန်လည်ဖွင့်ပေးပြီးပါပြီ',
            'user': UserSerializer(user, context={'request': request}).data
        })


class NewsletterSubscriberViewSet(viewsets.ModelViewSet):
    queryset = NewsletterSubscriber.objects.all()
    serializer_class = NewsletterSubscriberSerializer

    def get_permissions(self):
        if self.action in ['create']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), permissions.DjangoModelPermissions()]
