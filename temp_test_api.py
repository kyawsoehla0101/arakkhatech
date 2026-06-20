
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "arakkhatech.settings")
django.setup()

from django.test import Client

client = Client()

print("Testing /api/v1/:")
response = client.get("/api/v1/")
print(f"Status code: {response.status_code}")
if response.status_code >= 400:
    print(f"Error: {response.content.decode('utf-8')}")

print("\nTesting /api/v1/courses/:")
response_courses = client.get("/api/v1/courses/")
print(f"Status code: {response_courses.status_code}")
if response_courses.status_code >=400:
    print(f"Error: {response_courses.content.decode('utf-8')}")
