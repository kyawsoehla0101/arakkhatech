from django.contrib import admin
from .models import Book, Chapter

class ChapterInline(admin.StackedInline):
    model = Chapter
    extra = 1
    prepopulated_fields = {'slug': ('title',)}

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'course', 'is_free_book', 'order')
    list_filter = ('author', 'course', 'is_free_book')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'author__username')
    inlines = [ChapterInline]

    fieldsets = (
        ('စာအုပ်အချက်အလက်များ', {
            'fields': ('title', 'slug', 'description', 'thumbnail', 'author', 'order')
        }),
        ('ဆက်တင်များ', {
            'fields': ('is_free_book', 'course'),
            'description': 'စာအုပ်စင်မှာ ပြသချင်ရင် "Is free book" ကို အမှန်ခြစ်ပါ။ သင်တန်းနဲ့ ချိတ်ဆက်ချင်ရင် "Course" ကို ရွေးချယ်ပါ။'
        }),
    )

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('title', 'book', 'order', 'updated_at')
    list_filter = ('book',)
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'content')

    class Media:
        css = {
            'all': ('https://unpkg.com/easymde/dist/easymde.min.css',)
        }
        js = (
            'https://unpkg.com/easymde/dist/easymde.min.js',
            'js/admin_markdown.js',
        )
