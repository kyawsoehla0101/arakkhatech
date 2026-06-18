from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Book, Chapter
from courses.serializers import UserSerializer

class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = '__all__'

class BookSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    chapters = ChapterSerializer(many=True, read_only=True)
    
    class Meta:
        model = Book
        fields = '__all__'
