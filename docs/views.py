import markdown
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from .models import Book, Chapter
from .forms import BookForm, ChapterForm
from courses.models import Course

def is_admin(user):
    if user.is_superuser:
        return True
    if hasattr(user, 'profile'):
        return user.profile.role == 'admin'
    return False

def is_instructor(user):
    if user.is_superuser:
        return True
    if hasattr(user, 'profile'):
        return user.profile.role == 'instructor'
    return False

def can_manage_course(user, course):
    if is_admin(user):
        return True
    return course.instructor == user

def can_manage_book(user, book):
    if is_admin(user):
        return True
    return book.author == user

# Public Views
def docs_list(request):
    books = Book.objects.all().prefetch_related('chapters')
    free_books = books.filter(is_free_book=True)
    course_docs = books.filter(course__isnull=False)
    return render(request, 'docs/book_list.html', {
        'free_books': free_books,
        'course_docs': course_docs,
        'all_books': books
    })

def book_overview(request, slug):
    book = get_object_or_404(Book, slug=slug)
    chapters = book.chapters.all().order_by('order')
    return render(request, 'docs/book_overview.html', {
        'book': book,
        'chapters': chapters
    })

def chapter_detail(request, book_slug, slug):
    chapter = get_object_or_404(Chapter, book__slug=book_slug, slug=slug)
    book = chapter.book
    chapters = book.chapters.all().order_by('order')
    
    # Convert markdown to HTML with robust extension support
    content_html = markdown.markdown(chapter.content, extensions=[
        'extra', 'codehilite', 'toc', 'nl2br', 'sane_lists', 
        'fenced_code', 'attr_list', 'admonition',
    ])
    
    # Navigation
    chapter_list = list(chapters)
    chapter_index = chapter_list.index(chapter)
    prev_chapter = chapter_list[chapter_index - 1] if chapter_index > 0 else None
    next_chapter = chapter_list[chapter_index + 1] if chapter_index < len(chapter_list) - 1 else None
    
    return render(request, 'docs/chapter_detail.html', {
        'chapter': chapter,
        'book': book,
        'chapters': chapters,
        'content_html': content_html,
        'prev_page': prev_chapter,
        'next_page': next_chapter
    })

# Admin CRUD Views
@login_required
@user_passes_test(is_instructor)
def manage_books(request):
    query = request.GET.get('q', '')
    filter_type = request.GET.get('type', 'all')
    if is_admin(request.user):
        books = Book.objects.all().order_by('order')
    else:
        books = Book.objects.filter(author=request.user).order_by('order')
    
    if query:
        books = books.filter(Q(title__icontains=query) | Q(description__icontains=query))
    if filter_type == 'free':
        books = books.filter(is_free_book=True)
    elif filter_type == 'course':
        books = books.filter(course__isnull=False)
        
    return render(request, 'docs/management/manage_books.html', {
        'books': books,
        'query': query,
        'filter_type': filter_type
    })

@login_required
@user_passes_test(is_instructor)
def add_book(request):
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save(commit=False)
            if not is_admin(request.user):
                book.author = request.user
            book.save()
            messages.success(request, "စာအုပ်အသစ်ကို ထည့်သွင်းပြီးပါပြီ")
            return redirect('manage_books')
        else:
            messages.error(request, "အချက်အလက်များ မှားယွင်းနေပါသည်။ ပြန်လည်စစ်ဆေးပေးပါ။")
    else:
        form = BookForm()
        if not is_admin(request.user):
            # For instructors, only show their own courses in the form
            form.fields['course'].queryset = Course.objects.filter(instructor=request.user)
    return render(request, 'docs/management/book_form.html', {'form': form, 'title': 'စာအုပ်အသစ်ထည့်ရန်'})

@login_required
@user_passes_test(is_instructor)
def edit_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if not can_manage_book(request.user, book):
        messages.error(request, "ဤစာအုပ်ကို ပြင်ဆင်ခွင့်မရှိပါ။")
        return redirect('manage_books')
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            book = form.save(commit=False)
            if not is_admin(request.user):
                book.author = request.user
            book.save()
            messages.success(request, "စာအုပ်အချက်အလက်များကို ပြင်ဆင်ပြီးပါပြီ")
            return redirect('manage_books')
        else:
            messages.error(request, "အချက်အလက်များ မှားယွင်းနေပါသည်။ ပြန်လည်စစ်ဆေးပေးပါ။")
    else:
        form = BookForm(instance=book)
        if not is_admin(request.user):
            # For instructors, only show their own courses in the form
            form.fields['course'].queryset = Course.objects.filter(instructor=request.user)
    return render(request, 'docs/management/book_form.html', {'form': form, 'title': 'စာအုပ်ပြင်ဆင်ရန်'})

@login_required
@user_passes_test(is_instructor)
def delete_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if not can_manage_book(request.user, book):
        messages.error(request, "ဤစာအုပ်ကို ဖျက်သိမ်းခွင့်မရှိပါ။")
        return redirect('manage_books')
    if request.method == 'POST':
        book.delete()
        messages.success(request, "စာအုပ်ကို ဖျက်သိမ်းပြီးပါပြီ")
        return redirect('manage_books')
    return render(request, 'docs/management/confirm_delete.html', {'item': book, 'type': 'Book'})

# Chapter Management
@login_required
@user_passes_test(is_instructor)
def manage_chapters(request, book_pk):
    book = get_object_or_404(Book, pk=book_pk)
    if not can_manage_book(request.user, book):
        messages.error(request, "ဤစာအုပ်ကို ကြည့်ရှုခွင့်မရှိပါ။")
        return redirect('manage_books')
    chapters = book.chapters.all().order_by('order')
    return render(request, 'docs/management/manage_chapters.html', {'book': book, 'chapters': chapters})

@login_required
@user_passes_test(is_instructor)
def add_chapter(request, book_pk):
    book = get_object_or_404(Book, pk=book_pk)
    if not can_manage_book(request.user, book):
        messages.error(request, "ဤစာအုပ်အတွက် အခန်းထည့်ခွင့်မရှိပါ။")
        return redirect('manage_books')
    if request.method == 'POST':
        form = ChapterForm(request.POST)
        if form.is_valid():
            chapter = form.save(commit=False)
            chapter.book = book
            chapter.save()
            messages.success(request, "စာမျက်နှာအသစ်ကို ထည့်သွင်းပြီးပါပြီ")
            return redirect('manage_chapters', book_pk=book_pk)
        else:
            messages.error(request, "အချက်အလက်များ မှားယွင်းနေပါသည်။ ပြန်လည်စစ်ဆေးပေးပါ။")
    else:
        form = ChapterForm(initial={'book': book})
    return render(request, 'docs/management/chapter_form.html', {'form': form, 'book': book, 'title': 'စာမျက်နှာအသစ်ထည့်ရန်'})

@login_required
@user_passes_test(is_instructor)
def edit_chapter(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk)
    if not can_manage_book(request.user, chapter.book):
        messages.error(request, "ဤစာမျက်နှာကို ပြင်ဆင်ခွင့်မရှိပါ။")
        return redirect('manage_books')
    if request.method == 'POST':
        form = ChapterForm(request.POST, instance=chapter)
        if form.is_valid():
            form.save()
            messages.success(request, "စာမျက်နှာကို ပြင်ဆင်ပြီးပါပြီ")
            return redirect('manage_chapters', book_pk=chapter.book.pk)
        else:
            messages.error(request, "အချက်အလက်များ မှားယွင်းနေပါသည်။ ပြန်လည်စစ်ဆေးပေးပါ။")
    else:
        form = ChapterForm(instance=chapter)
    return render(request, 'docs/management/chapter_form.html', {'form': form, 'book': chapter.book, 'title': 'စာမျက်နှာပြင်ဆင်ရန်'})

@login_required
@user_passes_test(is_instructor)
def delete_chapter(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk)
    if not can_manage_book(request.user, chapter.book):
        messages.error(request, "ဤစာမျက်နှာကို ဖျက်သိမ်းခွင့်မရှိပါ။")
        return redirect('manage_books')
    book_pk = chapter.book.pk
    if request.method == 'POST':
        chapter.delete()
        messages.success(request, "စာမျက်နှာကို ဖျက်သိမ်းပြီးပါပြီ")
        return redirect('manage_chapters', book_pk=book_pk)
    return render(request, 'docs/management/confirm_delete.html', {'item': chapter, 'type': 'Chapter'})
