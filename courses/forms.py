from django import forms
from .models import Course, Lesson, Enrollment, CommunityVoice, Profile
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

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
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput) and not isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({
                    'class': 'block w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all font-medium text-slate-700 placeholder-slate-400'
                })

class CommunityVoiceForm(forms.ModelForm):
    class Meta:
        model = CommunityVoice
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'block w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-[2rem] focus:ring-2 focus:ring-indigo-500 outline-none transition-all text-sm font-medium leading-relaxed',
                'placeholder': 'သင့်၏ ထင်မြင်ယူဆချက် သို့မဟုတ် သင်ယူမှုအတွိအကြုံကို အေမှာ ရီးပီးပါ...',
                'rows': 4
            }),
        }
        labels = {
            'content': '',
        }

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
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': 'block w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all font-medium text-slate-700 placeholder-slate-400'
                })
        
        if 'description' in self.fields:
            self.fields['description'].widget.attrs.update({'class': self.fields['description'].widget.attrs.get('class', '') + ' editor'})

class StudentCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'block w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-[2rem] focus:ring-2 focus:ring-indigo-500 outline-none transition-all font-medium text-slate-700 placeholder-slate-400'
            })

class ManualEnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['student', 'course']
        widgets = {
            'student': forms.Select(attrs={'class': 'block w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all'}),
            'course': forms.Select(attrs={'class': 'block w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all'}),
        }

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['course', 'title', 'content', 'video_url', 'video_file', 'video_poster', 'duration', 'order']
        widgets = {
            'course': forms.Select(attrs={'class': 'block w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all'}),
            'title': forms.TextInput(attrs={'class': 'block w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all'}),
            'content': forms.Textarea(attrs={'class': 'block w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all editor', 'rows': 10}),
            'video_url': forms.URLInput(attrs={'class': 'block w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all'}),
            'video_file': forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'}),
            'video_poster': forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'}),
            'duration': forms.TextInput(attrs={'class': 'block w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all', 'placeholder': 'e.g. 10:25'}),
            'order': forms.NumberInput(attrs={'class': 'block w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': 'block w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all font-medium text-slate-700 placeholder-slate-400'
                })
        
        if 'content' in self.fields:
            self.fields['content'].widget.attrs.update({'class': self.fields['content'].widget.attrs.get('class', '') + ' editor'})
