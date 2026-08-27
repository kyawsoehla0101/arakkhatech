from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from .models import (
    Course, Lesson, Enrollment, Notification,
    CommunityVoice, Profile, NewsletterSubscriber
)
from .helpers import is_admin, is_instructor


class ProfileSerializer(serializers.ModelSerializer):
    role_label = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['id', 'avatar', 'bio', 'role', 'role_label']

    def get_role_label(self, obj):
        return obj.get_role_display() if obj else None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = kwargs.get('context', {})
        request = context.get('request')
        if request and request.user and not is_admin(request.user):
            self.fields['role'].read_only = True


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    role = serializers.CharField(source='profile.role', read_only=True)
    role_label = serializers.CharField(source='profile.get_role_display', read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name',
                  'is_active', 'date_joined', 'profile', 'role', 'role_label']
        read_only_fields = ['id', 'date_joined']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    role = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password_confirm', 'role']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("ဤအီးမေးလ်ဖြင့် အကောင့်ရှိပြီးသားဖြစ်ပါသည်")
        return value

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'လျှို့ဝှက်နံပါတ်များ ကိုက်ညီမှုမရှိပါ'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.is_active = True
        user.save()
        profile, _ = Profile.objects.get_or_create(user=user, defaults={'role': 'student'})
        if profile.role != 'student':
            profile.role = 'student'
            profile.save(update_fields=['role'])
        return user


class UserAdminCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    role = serializers.ChoiceField(
        choices=[('student', 'ကျောင်းသား'), ('instructor', 'သင်တန်းဆရာ'), ('admin', 'အုပ်ချုပ်ရေးမှူး')],
        required=False,
        default='student'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'is_active', 'role']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("ဤအီးမေးလ်ဖြင့် အကောင့်ရှိပြီးသားဖြစ်ပါသည်")
        return value

    def create(self, validated_data):
        role = validated_data.pop('role', 'student')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        if not validated_data.get('is_active') is False:
            user.is_active = True
        user.save()
        profile, _ = Profile.objects.get_or_create(user=user, defaults={'role': role})
        if profile.role != role:
            profile.role = role
            profile.save(update_fields=['role'])
        return user


class UserAdminUpdateSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(
        choices=[('student', 'ကျောင်းသား'), ('instructor', 'သင်တန်းဆရာ'), ('admin', 'အုပ်ချုပ်ရေးမှူး')],
        required=False
    )
    new_password = serializers.CharField(
        write_only=True,
        required=False,
        validators=[validate_password],
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active', 'role', 'new_password']

    def validate_email(self, value):
        user_pk = self.instance.pk if self.instance else None
        if User.objects.filter(email__iexact=value).exclude(pk=user_pk).exists():
            raise serializers.ValidationError("ဤအီးမေးလ်ဖြင့် အခြားအကောင့်ရှိပြီးသားဖြစ်ပါသည်")
        return value

    def validate_username(self, value):
        user_pk = self.instance.pk if self.instance else None
        if User.objects.filter(username__iexact=value).exclude(pk=user_pk).exists():
            raise serializers.ValidationError("ဤအသုံးပြုသူအမည် ရှိပြီးသားဖြစ်ပါသည်")
        return value

    def update(self, instance, validated_data):
        role = validated_data.pop('role', None)
        new_password = validated_data.pop('new_password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if new_password:
            instance.set_password(new_password)
        instance.save()
        if role and hasattr(instance, 'profile'):
            if instance.profile.role != role:
                instance.profile.role = role
                instance.profile.save(update_fields=['role'])
        return instance


class UserChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, required=True, validators=[validate_password], style={'input_type': 'password'})
    new_password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'နောက်ဆုံးထပ်ရိုက်ထားသော လျှို့ဝှက်နံပါတ်နှင့် ကိုက်ညီမှုမရှိပါ'})
        return attrs


class LessonSerializer(serializers.ModelSerializer):
    youtube_id = serializers.CharField(read_only=True)

    class Meta:
        model = Lesson
        fields = '__all__'


class CourseSerializer(serializers.ModelSerializer):
    instructor = UserSerializer(read_only=True)
    lessons = LessonSerializer(many=True, read_only=True)
    enrollment_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = '__all__'

    def get_enrollment_count(self, obj):
        return obj.enrolled_students.count()


class EnrollmentSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    progress_percentage = serializers.IntegerField(read_only=True)

    class Meta:
        model = Enrollment
        fields = '__all__'


class InstructorEnrollStudentSerializer(serializers.Serializer):
    username_or_email = serializers.CharField(
        required=True,
        help_text="ကျောင်းသားရဲ့ Username (သို့မဟုတ်) အီးမေးလ်ဖြင့် ရှာပြီး စာရင်းသွင်းပေးမည်"
    )
    course_id = serializers.IntegerField(
        required=True,
        help_text="စာရင်းသွင်းမည့် သင်တန်း ID"
    )

    def validate_username_or_email(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError("Username / အီးမေးလ် ဖြည့်ပေးပါ")
        return str(value).strip()

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user if request else None
        if not user or not user.is_authenticated:
            raise serializers.ValidationError("လုပ်ပိုင်ခွင့်မရှိပါ")

        lookup = attrs.get('username_or_email')
        student = User.objects.filter(
            Q(username__iexact=lookup) | Q(email__iexact=lookup)
        ).first()
        if not student:
            raise serializers.ValidationError({'username_or_email': "မှတ်တမ်းမတွေ့ပါ။ Username / Email ကို ပြန်စစ်ပေးပါ"})

        if hasattr(student, 'profile') and student.profile.role and student.profile.role != 'student':
            raise serializers.ValidationError({
                'username_or_email': f"ဤအကောင့်သည် {student.profile.get_role_display()} ဖြစ်သောကြောင့် ကျောင်းသားအဖြစ် စာရင်းမသွင်းနိုင်ပါ"
            })

        course_id = attrs.get('course_id')
        course = Course.objects.filter(pk=course_id).first()
        if not course:
            raise serializers.ValidationError({'course_id': "သင်တန်းမတွေ့ပါ"})

        if not is_admin(user) and course.instructor_id != getattr(user, 'pk', None):
            raise serializers.ValidationError({'course_id': "ဤသင်တန်းကို စီမံခွင့်မရှိပါ"})

        if Enrollment.objects.filter(student=student, course=course).exists():
            raise serializers.ValidationError("ဤကျောင်းသားသည် သင်တန်းသို့ အရင်ကစာရင်းသွင်းပြီးသားဖြစ်ပါသည်")

        attrs['_student'] = student
        attrs['_course'] = course
        return attrs


class CommunityVoiceSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = CommunityVoice
        fields = '__all__'
        read_only_fields = ['user', 'is_approved']


class NotificationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['user']


class NewsletterSubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscriber
        fields = '__all__'
