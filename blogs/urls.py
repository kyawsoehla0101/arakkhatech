from django.urls import path
from . import views

app_name = 'blogs'

urlpatterns = [
    path('', views.blog_list, name='blog_list'),
    path('<slug:slug>/', views.blog_detail, name='blog_detail'),
    
    # Management CRUD
    path('manage/list/', views.manage_blogs, name='manage_blogs'),
    path('manage/add/', views.add_blog, name='add_blog'),
    path('manage/edit/<int:pk>/', views.edit_blog, name='edit_blog'),
    path('manage/delete/<int:pk>/', views.delete_blog, name='delete_blog'),
]
