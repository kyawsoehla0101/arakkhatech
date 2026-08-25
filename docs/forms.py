from django import forms
from django.contrib.auth.models import User
from .models import Book, Chapter
from courses.models import Course
from courses.helpers import is_admin as _is_admin

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'description', 'thumbnail', 'order', 'course', 'author', 'is_free_book']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 border border-slate-100 rounded-2xl px-6 py-4 text-sm font-bold outline-none focus:ring-2 focus:ring-indigo-500 transition-all',
                'placeholder': 'စာအုပ်အမည် ဖြည့်စွက်ပါ...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full bg-slate-50 border border-slate-100 rounded-2xl px-6 py-4 text-sm font-bold outline-none focus:ring-2 focus:ring-indigo-500 transition-all',
                'rows': 4,
                'placeholder': 'စာအုပ်အကျဉ်းချုပ် ရေးသားပါ...'
            }),
            'thumbnail': forms.FileInput(attrs={'class': 'w-full bg-slate-50 border border-slate-100 rounded-2xl px-6 py-4 text-sm font-bold outline-none focus:ring-2 focus:ring-indigo-500 transition-all'}),
            'order': forms.NumberInput(attrs={'class': 'w-full bg-slate-50 border border-slate-100 rounded-2xl px-6 py-4 text-sm font-bold outline-none focus:ring-2 focus:ring-indigo-500 transition-all'}),
            'course': forms.Select(attrs={'class': 'w-full bg-slate-50 border border-slate-100 rounded-2xl px-6 py-4 text-sm font-bold outline-none focus:ring-2 focus:ring-indigo-500 transition-all'}),
            'author': forms.Select(attrs={'class': 'w-full bg-slate-50 border border-slate-100 rounded-2xl px-6 py-4 text-sm font-bold outline-none focus:ring-2 focus:ring-indigo-500 transition-all'}),
            'is_free_book': forms.CheckboxInput(attrs={'class': 'rounded border-slate-300 text-indigo-600 focus:ring-indigo-500'}),
        }

    def __init__(self, *args, **kwargs):
        editing_user = kwargs.pop('editing_user', None)
        super().__init__(*args, **kwargs)
        self._editing_user = editing_user

        if 'course' in self.fields:
            self.fields['course'].required = False
            self.fields['course'].empty_label = '-- လိုင်စင် (နေရွေးချယ်) --'
            if editing_user is not None and not _is_admin(editing_user):
                self.fields['course'].queryset = Course.objects.filter(instructor=editing_user)
            else:
                self.fields['course'].queryset = Course.objects.all().select_related('instructor')

        if 'author' in self.fields:
            self.fields['author'].required = True
            self.fields['author'].empty_label = None
            from courses.helpers import is_instructor as _is_instructor
            author_ids = [u.id for u in User.objects.all().select_related('profile') if _is_instructor(u)]
            if editing_user is not None and _is_instructor(editing_user) and editing_user.id not in author_ids:
                author_ids.append(editing_user.id)
            self.fields['author'].queryset = User.objects.filter(id__in=author_ids).select_related('profile')
            if editing_user is not None and not _is_admin(editing_user):
                self.fields['author'].disabled = True
                self.fields['author'].widget.attrs['readonly'] = True
                if not self.instance or not self.instance.pk or not self.instance.author_id:
                    self.initial['author'] = editing_user.id

    def clean_author(self):
        author = self.cleaned_data.get('author')
        if self._editing_user is not None and not _is_admin(self._editing_user):
            return self._editing_user
        if not author:
            if self._editing_user is not None:
                return self._editing_user
            raise forms.ValidationError("Author ကို ရွေးချယ်ပေးပါ")
        from courses.helpers import is_instructor as _is_instructor
        if not _is_instructor(author):
            raise forms.ValidationError("ရွေးချယ်ထားသူသည် Instructor role မဟုတ်ပါ")
        return author

class ChapterForm(forms.ModelForm):
    class Meta:
        model = Chapter
        fields = ['book', 'title', 'content', 'order']
        widgets = {
            'book': forms.Select(attrs={'class': 'w-full bg-slate-50 border border-slate-100 rounded-2xl px-6 py-4 text-sm font-bold outline-none focus:ring-2 focus:ring-indigo-500 transition-all'}),
            'title': forms.TextInput(attrs={'class': 'w-full bg-slate-50 border border-slate-100 rounded-2xl px-6 py-4 text-sm font-bold outline-none focus:ring-2 focus:ring-indigo-500 transition-all'}),
            'content': forms.Textarea(attrs={'class': 'w-full bg-slate-50 border border-slate-100 rounded-2xl px-6 py-4 text-sm font-bold outline-none focus:ring-2 focus:ring-indigo-500 transition-all', 'rows': 10, 'id': 'markdown-editor'}),
            'order': forms.NumberInput(attrs={'class': 'w-full bg-slate-50 border border-slate-100 rounded-2xl px-6 py-4 text-sm font-bold outline-none focus:ring-2 focus:ring-indigo-500 transition-all'}),
        }

    def __init__(self, *args, **kwargs):
        book = kwargs.pop('book', None)
        editing_user = kwargs.pop('editing_user', None)
        super().__init__(*args, **kwargs)
        self._editing_user = editing_user

        if 'book' in self.fields:
            if editing_user is not None and not _is_admin(editing_user):
                allowed_books = Book.objects.filter(author=editing_user)
                if self.instance and self.instance.book_id:
                    if not allowed_books.filter(id=self.instance.book_id).exists():
                        allowed_books = allowed_books | Book.objects.filter(id=self.instance.book_id)
                self.fields['book'].queryset = allowed_books
                self.fields['book'].disabled = True
                self.fields['book'].widget.attrs['readonly'] = True
            else:
                self.fields['book'].queryset = Book.objects.all()

        if book:
            self.initial['book'] = book
            self.fields['book'].disabled = True
            self.fields['book'].widget.attrs['readonly'] = True
