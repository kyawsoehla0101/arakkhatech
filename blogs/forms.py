from django import forms
from .models import Post

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'slug', 'thumbnail', 'content', 'status']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 border-slate-200 rounded-2xl px-6 py-4 text-sm font-bold focus:ring-2 focus:ring-blue-500 outline-none transition-all',
                'placeholder': 'Enter blog title...'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 border-slate-200 rounded-2xl px-6 py-4 text-sm font-bold focus:ring-2 focus:ring-blue-500 outline-none transition-all',
                'placeholder': 'blog-slug-url'
            }),
            'thumbnail': forms.FileInput(attrs={
                'class': 'w-full bg-slate-50 border-slate-200 rounded-2xl px-6 py-4 text-sm font-bold focus:ring-2 focus:ring-blue-500 outline-none transition-all',
            }),
            'content': forms.Textarea(attrs={
                'id': 'tinymce-editor',
                'class': 'w-full bg-slate-50 border-slate-200 rounded-2xl px-6 py-4 text-sm font-bold focus:ring-2 focus:ring-blue-500 outline-none transition-all',
                'rows': 15
            }),
            'status': forms.Select(attrs={
                'class': 'w-full bg-slate-50 border-slate-200 rounded-2xl px-6 py-4 text-sm font-bold focus:ring-2 focus:ring-blue-500 outline-none transition-all',
            }),
        }
