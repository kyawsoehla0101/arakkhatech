from django.urls import path
from . import views

urlpatterns = [
    # Public List
    path('', views.docs_list, name='docs_list'),
    
    # Admin Management
    path('manage/', views.manage_books, name='manage_books'),
    path('manage/add/', views.add_book, name='add_book'),
    path('manage/<int:pk>/edit/', views.edit_book, name='edit_book'),
    path('manage/<int:pk>/delete/', views.delete_book, name='delete_book'),
    
    # Chapter Management
    path('manage/<int:book_pk>/chapters/', views.manage_chapters, name='manage_chapters'),
    path('manage/<int:book_pk>/chapters/add/', views.add_chapter, name='add_chapter'),
    path('manage/chapters/<int:pk>/edit/', views.edit_chapter, name='edit_chapter'),
    path('manage/chapters/<int:pk>/delete/', views.delete_chapter, name='delete_chapter'),

    # Public Detail (Move to bottom to avoid catching 'manage/')
    path('<str:slug>/', views.book_overview, name='book_overview'),
    path('<str:book_slug>/<str:slug>/', views.chapter_detail, name='chapter_detail'),
]
