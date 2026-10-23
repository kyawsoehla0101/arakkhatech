import markdown
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Post
from .forms import PostForm
from courses.helpers import is_instructor, is_admin

def blog_list(request):
    posts = Post.objects.filter(status='published')
    return render(request, 'blogs/blog_list.html', {'posts': posts,'active_nav': 'blogs'})

def blog_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, status='published')

    # Convert post.content markdown to HTML with full extension support
    try:
        content_html = markdown.markdown(post.content or '', extensions=[
            'extra', 'codehilite', 'toc', 'nl2br', 'sane_lists',
            'fenced_code', 'attr_list', 'admonition',
        ])
    except Exception:
        content_html = post.content or ''

    return render(request, 'blogs/blog_detail.html', {'post': post, 'content_html': content_html})

# --- Admin Dashboard CRUD ---

@login_required
@user_passes_test(is_instructor)
def manage_blogs(request):
    if is_admin(request.user):
        posts = Post.objects.all().order_by('-created_at')
    else:
        posts = Post.objects.filter(author=request.user).order_by('-created_at')
    return render(request, 'blogs/management/manage_blogs.html', {'posts': posts})

@login_required
@user_passes_test(is_instructor)
def add_blog(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, "ဆောင်းပါးအသစ်ကို အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ")
            return redirect('blogs:manage_blogs')
        else:
            messages.error(request, "အချက်အလက်များ မှားယွင်းနေပါသည်။ ပြန်လည်စစ်ဆေးပေးပါ။")
    else:
        form = PostForm()
    return render(request, 'blogs/management/blog_form.html', {'form': form, 'title': 'ဆောင်းပါးအသစ်ရေးရန်'})

@login_required
@user_passes_test(is_instructor)
def edit_blog(request, pk):
    post = get_object_or_404(Post, pk=pk)
    # Check permission
    if not is_admin(request.user) and post.author != request.user:
        messages.error(request, "ဤဆောင်းပါးကို ပြင်ဆင်ခွင့်မရှိပါ။")
        return redirect('blogs:manage_blogs')
        
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "ဆောင်းပါးကို အောင်မြင်စွာ ပြင်ဆင်ပြီးပါပြီ")
            return redirect('blogs:manage_blogs')
        else:
            messages.error(request, "အချက်အလက်များ မှားယွင်းနေပါသည်။ ပြန်လည်စစ်ဆေးပေးပါ။")
    else:
        form = PostForm(instance=post)
    return render(request, 'blogs/management/blog_form.html', {'form': form, 'title': 'ဆောင်းပါးပြင်ဆင်ရန်', 'post': post})

@login_required
@user_passes_test(is_instructor)
def delete_blog(request, pk):
    post = get_object_or_404(Post, pk=pk)
    # Check permission
    if not is_admin(request.user) and post.author != request.user:
        messages.error(request, "ဤဆောင်းပါးကို ဖျက်ခွင့်မရှိပါ။")
        return redirect('blogs:manage_blogs')
        
    if request.method == 'POST':
        post.delete()
        messages.success(request, "ဆောင်းပါးကို အောင်မြင်စွာ ဖျက်ဆီးပြီးပါပြီ")
        return redirect('blogs:manage_blogs')
    return render(request, 'blogs/management/blog_confirm_delete.html', {'post': post})
