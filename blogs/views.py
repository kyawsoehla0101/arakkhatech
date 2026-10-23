from django.shortcuts import render, get_object_or_404
from .models import Post

def blog_list(request):
    posts = Post.objects.filter(status='published')
    return render(request, 'blogs/blog_list.html', {'posts': posts})

def blog_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, status='published')
    return render(request, 'blogs/blog_detail.html', {'post': post})
