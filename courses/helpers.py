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
