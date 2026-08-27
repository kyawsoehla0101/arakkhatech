from django import forms
from .models import Course, Lesson, Enrollment, CommunityVoice, Profile
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .helpers import is_admin as _is_admin, is_instructor as _is_instructor

class SignUpForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=100,
        required=False,
        label='နာမည် (Optional)',
        widget=forms.TextInput(attrs={
            'class': 'block w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all font-medium',
            'placeholder': 'ဥပမာ- ကျော်ဦး'
        })
    )
    last_name = forms.CharField(
        max_length=100,
        required=False,
        label='မျိုးရိုးနာမည် (Optional)',
        widget=forms.TextInput(attrs={
            'class': 'block w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all font-medium',
            'placeholder': 'ဥပမာ- စိုး'
        })
    )
    email = forms.EmailField(
        max_length=254,
        required=True,
        label='အီးမေးလ်',
        widget=forms.EmailInput(attrs={
            'class': 'block w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all font-medium',
            'placeholder': 'you@example.com'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'block w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all font-medium',
            'placeholder': 'အသုံးပြုသူအမည်'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'block w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all font-medium',
            'placeholder': '••••••••'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'block w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all font-medium',
            'placeholder': 'နောက်တစ်ခါထပ်ရိုက်ပါ'
        })
        self.fields['username'].label = 'အသုံးပြုသူအမည်'
        self.fields['password1'].label = 'လျှို့ဝှက်နံပါတ်'
        self.fields['password2'].label = 'လျှို့ဝှက်နံပါတ်အတည်ပြုရန်'

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'block w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-[2rem] focus:ring-2 focus:ring-indigo-500 outline-none transition-all text-sm font-medium', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'block w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-[2rem] focus:ring-2 focus:ring-indigo-500 outline-none transition-all text-sm font-medium', 'placeholder': 'Last Name'}),
        }

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar', 'bio', 'role']
        widgets = {
            'avatar': forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'}),
            'bio': forms.Textarea(attrs={'class': 'block w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-[2rem] focus:ring-2 focus:ring-indigo-500 outline-none transition-all text-sm font-medium leading-relaxed', 'rows': 3, 'placeholder': 'သင့်အကြောင်း အနည်းငယ် ရေးသားပါ...'}),
            'role': forms.Select(attrs={'class': 'block w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all font-medium text-slate-700'}),
        }

    def __init__(self, *args, **kwargs):
        editing_user = kwargs.pop('editing_user', None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput) and not isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({
                    'class': 'block w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all font-medium text-slate-700 placeholder-slate-400'
                })
        if editing_user is not None and not _is_admin(editing_user):
            self.fields['role'].disabled = True
            self.fields['role'].widget.attrs['readonly'] = True
        self._editing_user = editing_user

    def clean_role(self):
        if self._editing_user is not None and not _is_admin(self._editing_user):
            if self.instance and self.instance.pk:
                return self.instance.role
            return self.cleaned_data.get('role') or 'student'
        return self.cleaned_data.get('role') or 'student'

class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254, help_text='လိုအပ်ပါတယ်။ မှန်ကန်တဲ့ email လိပိပေးပါ။')
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2',)

    def __init__(self, *args, **kwargs):
        super(SignUpForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-[2rem] focus:ring-2 focus:ring-indigo-500 outline-none transition-all'
            field.help_text = None

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'thumbnail', 'instructor']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'block w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all'}),
            'description': forms.Textarea(attrs={'class': 'block w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all editor', 'rows': 6}),
            'thumbnail': forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'}),
            'instructor': forms.Select(attrs={'class': 'block w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all'}),
        }

    def __init__(self, *args, **kwargs):
        editing_user = kwargs.pop('editing_user', None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': 'block w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all font-medium text-slate-700 placeholder-slate-400'
                })
        
        if 'description' in self.fields:
            self.fields['description'].widget.attrs.update({'class': self.fields['description'].widget.attrs.get('class', '') + ' editor'})

        instructor_ids = []
        for user in User.objects.all().select_related('profile'):
            if _is_instructor(user):
                instructor_ids.append(user.id)
        if editing_user is not None and _is_instructor(editing_user) and editing_user.id not in instructor_ids:
            instructor_ids.append(editing_user.id)
        instructor_qs = User.objects.filter(id__in=instructor_ids).select_related('profile')
        self.fields['instructor'].queryset = instructor_qs
        self.fields['instructor'].empty_label = None

        if editing_user is not None and not _is_admin(editing_user):
            self.fields['instructor'].disabled = True
            self.fields['instructor'].widget.attrs['readonly'] = True
            if not self.instance or not self.instance.pk or not self.instance.instructor_id:
                self.initial['instructor'] = editing_user.id
        self._editing_user = editing_user

    def clean_instructor(self):
        instructor = self.cleaned_data.get('instructor')
        if self._editing_user is not None and not _is_admin(self._editing_user):
            return self._editing_user
        if not instructor:
            if self._editing_user is not None:
                return self._editing_user
            raise forms.ValidationError("Instructor ကို ရွေးချယ်ပေးပါ")
        if not _is_instructor(instructor):
            if self._editing_user is not None and _is_instructor(self._editing_user):
                return self._editing_user
            raise forms.ValidationError("ရွေးချယ်ထားသူသည် Instructor role မဟုတ်ပါ")
        return instructor

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['course', 'title', 'video_url', 'video_file', 'video_poster', 'duration', 'content', 'order']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'block w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all', 'placeholder': 'သင်ခန်းစာခေါင်းစဉ်...'}),
            'video_url': forms.URLInput(attrs={'class': 'block w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all', 'placeholder': 'https://www.youtube.com/watch?v=... (သို့) အခြား Video URL'}),
            'video_file': forms.FileInput(attrs={'class': 'block w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all text-sm text-slate-500 file:mr-4 file:py-2.5 file:px-5 file:rounded-2xl file:border-0 file:text-sm file:font-bold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 transition-all', 'accept': 'video/*,audio/*,.mp4,.mov,.mkv,.webm'}),
            'video_poster': forms.FileInput(attrs={'class': 'block w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all text-sm text-slate-500 file:mr-4 file:py-2.5 file:px-5 file:rounded-2xl file:border-0 file:text-sm file:font-bold file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200 transition-all', 'accept': 'image/*'}),
            'duration': forms.TextInput(attrs={'class': 'block w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all', 'placeholder': 'ဥပမာ- 10:25'}),
            'content': forms.Textarea(attrs={'id': 'markdown-editor', 'class': 'block w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all', 'rows': 12, 'placeholder': 'သင်ခန်းစာအကြောင်းအရာရေးသားပါ...'}),
            'order': forms.NumberInput(attrs={'class': 'block w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all', 'min': 0}),
        }
        help_texts = {
            'video_url': 'YouTube / Vimeo စသည့် video လိပ်ပြာကို တိုက်ရိုက်ထည့်နိုင်ပါတယ်',
            'video_file': 'သင့်စက်ထဲမှ ဗီဒီယိုဖိုင်ကို တိုက်ရိုက်တင်နိုင်ပါတယ်',
            'video_poster': 'ဗီဒီယိုကို မစကြည့်ခင် ပြသမယ့် အပြင်ဓာတ်ပုံ (Optional)',
            'duration': 'ဗီဒီယိုအတိုင်းအတာ ကြာချိန်',
        }

    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)
        user = kwargs.pop('user', None)
        super(LessonForm, self).__init__(*args, **kwargs)
        
        for field in self.fields.values():
            field.widget.attrs['class'] = 'w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all font-medium text-slate-700'
        
        if user is not None and not _is_admin(user):
            course_ids = list(Course.objects.filter(instructor=user).values_list('id', flat=True))
            if self.instance and self.instance.course_id:
                if self.instance.course_id not in course_ids:
                    course_ids.append(self.instance.course_id)
            self.fields['course'].queryset = Course.objects.filter(id__in=course_ids)
            self.fields['course'].disabled = True
            self.fields['course'].widget.attrs['readonly'] = True

        if course:
            self.initial['course'] = course
            self.fields['course'].disabled = True
            self.fields['course'].widget.attrs['readonly'] = True
        
        if 'content' in self.fields:
            self.fields['content'].widget.attrs['class'] += ' editor'

class CommunityVoiceForm(forms.ModelForm):
    class Meta:
        model = CommunityVoice
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'block w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all', 'rows': 6, 'placeholder': 'သင့်အသံထွက်မှုကို ဤနေရာတွင် ရေးသားပါ...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all font-medium text-slate-700 placeholder-slate-400'


class StudentCreationForm(UserCreationForm):
    email = forms.EmailField(max_length=254, required=True)
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all font-medium text-slate-700'
            field.help_text = None


class ManualEnrollmentForm(forms.Form):
    course = forms.ModelChoiceField(
        queryset=Course.objects.none(),
        required=True,
        label="သင်တန်းရွေးချယ်ပါ",
        widget=forms.Select(attrs={'class': 'w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all font-medium text-slate-700'})
    )
    username_or_email = forms.CharField(
        max_length=254,
        required=True,
        label="ကျောင်းသားရဲ့ Username (သို့) Email ထည့်ပါ",
        help_text="ကျောင်းသားရဲ့ account username ဒါမှမဟုတ် email လိပ်ပြာကို ရိုက်ထည့်ပါ",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all font-medium text-slate-700 placeholder-slate-400',
            'placeholder': 'ဥပမာ- kyawzayar123 ဒါမှမဟုတ် kyaw@example.com',
            'autocomplete': 'off'
        })
    )
    student = None
    _user = None
    _student_obj = None

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        initial = kwargs.get('initial', {}) or {}
        if 'student' in initial and hasattr(initial['student'], 'username'):
            initial['username_or_email'] = initial['student'].username
            kwargs['initial'] = initial
        super().__init__(*args, **kwargs)
        self._user = user
        for field in self.fields.values():
            field.widget.attrs.setdefault(
                'class',
                'w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all font-medium text-slate-700'
            )
        if user is not None and not _is_admin(user):
            self.fields['course'].queryset = Course.objects.filter(instructor=user)
        else:
            self.fields['course'].queryset = Course.objects.all().select_related('instructor')

    def clean_username_or_email(self):
        query = self.cleaned_data.get('username_or_email', '').strip()
        if not query:
            raise forms.ValidationError("Username (သို့) Email ကို ထည့်ပေးပါ")

        from django.db.models import Q
        candidates = User.objects.select_related('profile').filter(
            Q(username__iexact=query) | Q(email__iexact=query)
        ).distinct()

        if not candidates.exists():
            raise forms.ValidationError(
                f"'{query}' နှင့်ကိုက်ညီတဲ့ ကျောင်းသားမတွေ့ရှိပါ။ ကျောင်းသားအား အရင်စာရင်းသွင်းပေးပါ။"
            )

        student = candidates.first()
        profile = getattr(student, 'profile', None)
        if profile and profile.role not in (None, '', 'student'):
            if profile.role == 'instructor' or profile.role == 'admin' or student.is_superuser or student.is_staff:
                raise forms.ValidationError(
                    f"'{student.username}' သည် {profile.role} role ရှိသည့်အတွက် course ကို enroll လုပ်လို့မရပါ။"
                )
        self._student_obj = student
        return query

    def clean(self):
        cleaned_data = super().clean()
        course = cleaned_data.get('course')
        student = self._student_obj
        if course and student:
            if Enrollment.objects.filter(course=course, student=student).exists():
                raise forms.ValidationError(
                    f"{student.username} သည် '{course.title}' သင်တန်းကို အရင်ကတည်းက စာရင်းသွင်းထားပြီးသားဖြစ်ပါတယ်။"
                )
            if self._user is not None and not _is_admin(self._user):
                if course.instructor_id != self._user.id:
                    raise forms.ValidationError("ဤသင်တန်းကို enroll လုပ်ပေးခွင့်မရှိပါ")
        return cleaned_data

    def save(self, commit=True):
        course = self.cleaned_data.get('course')
        student = self._student_obj
        enrollment = Enrollment(course=course, student=student)
        if commit:
            enrollment.save()
        return enrollment
