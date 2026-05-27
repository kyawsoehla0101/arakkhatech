from django import forms
from .models import Book, Chapter

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'description', 'thumbnail', 'order']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 border-none rounded-2xl px-6 py-4 text-sm font-bold outline-none focus:ring-2 focus:ring-indigo-500 transition-all',
                'placeholder': 'စာအုပ်အမည် ဖြည့်စွက်ပါ...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full bg-slate-50 border-none rounded-2xl px-6 py-4 text-sm font-bold outline-none focus:ring-2 focus:ring-indigo-500 transition-all',
                'rows': 4,
                'placeholder': 'စာအုပ်အကျဉ်းချုပ် ရေးသားပါ...'
            }),
            'thumbnail': forms.FileInput(attrs={'class': 'w-full bg-slate-50 border-none rounded-2xl px-6 py-4 text-sm font-bold outline-none focus:ring-2 focus:ring-indigo-500 transition-all'}),
            'order': forms.NumberInput(attrs={'class': 'w-full bg-slate-50 border-none rounded-2xl px-6 py-4 text-sm font-bold outline-none focus:ring-2 focus:ring-indigo-500 transition-all'}),
        }

class ChapterForm(forms.ModelForm):
    class Meta:
        model = Chapter
        fields = ['book', 'title', 'content', 'order']
        widgets = {
            'book': forms.Select(attrs={'class': 'w-full bg-slate-50 border-none rounded-2xl px-6 py-4 text-sm font-bold outline-none focus:ring-2 focus:ring-indigo-500 transition-all'}),
            'title': forms.TextInput(attrs={'class': 'w-full bg-slate-50 border-none rounded-2xl px-6 py-4 text-sm font-bold outline-none focus:ring-2 focus:ring-indigo-500 transition-all'}),
            'content': forms.Textarea(attrs={'class': 'w-full bg-slate-50 border-none rounded-2xl px-6 py-4 text-sm font-bold outline-none focus:ring-2 focus:ring-indigo-500 transition-all', 'rows': 10, 'id': 'markdown-editor'}),
            'order': forms.NumberInput(attrs={'class': 'w-full bg-slate-50 border-none rounded-2xl px-6 py-4 text-sm font-bold outline-none focus:ring-2 focus:ring-indigo-500 transition-all'}),
        }
