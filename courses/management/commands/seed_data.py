from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from courses.models import Course, Lesson

class Command(BaseCommand):
    help = 'Populates the database with initial seed data'

    def handle(self, *args, **kwargs):
        # Create superuser if it doesn't exist
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            self.stdout.write(self.style.SUCCESS("Superuser created: admin / admin123"))

        admin_user = User.objects.get(username='admin')

        # 1. Python Course
        course1, _ = Course.objects.get_or_create(
            title="Python အခြေခံမှ အဆင့်မြင့်အထိ",
            defaults={
                'description': "ဤသင်တန်းတွင် Python programming language ၏ အခြေခံသဘောတရားများမှစ၍ အဆင့်မြင့် coding ရေးသားနည်းများအထိ လေ့လာရမည်ဖြစ်ပါသည်။",
                'instructor': admin_user
            }
        )

        python_lessons = [
            ("Python ဆိုတာဘာလဲ?", "Python သည် အဆင့်မြင့် programming language တစ်ခုဖြစ်ပြီး ဖတ်ရလွယ်ကူခြင်းနှင့် ရိုးရှင်းခြင်းကြောင့် လူကြိုက်များပါသည်။", "https://www.youtube.com/watch?v=rfscVS0vtbw", "10:00"),
            ("Variables နှင့် Data Types", "Variables များသည် data များကို သိမ်းဆည်းရန် နေရာများဖြစ်ပါသည်။ Python တွင် string, integer, float, boolean စသည့် data type များရှိပါသည်။", "https://www.youtube.com/watch?v=vLqTf2b6GZw", "15:30"),
            ("Python Lists များအကြောင်း", "Lists များသည် data အများအပြားကို တစ်နေရာတည်းတွင် သိမ်းဆည်းရန် အသုံးပြုပါသည်။", "https://www.youtube.com/watch?v=9OeznAkyQz4", "12:00"),
            ("Dictionaries နှင့် Tuples", "Key-value pairs များဖြင့် data သိမ်းဆည်းပုံနှင့် ပြောင်းလဲ၍မရသော Tuples များအကြောင်း။", "https://www.youtube.com/watch?v=daefaLgNkw0", "14:20"),
            ("If-Else Conditional Statements", "ဆုံးဖြတ်ချက်များချရန် logic ရေးသားနည်းများ။", "https://www.youtube.com/watch?v=DZwmZ8Ot-Sg", "08:45"),
            ("For Loops နှင့် While Loops", "အလုပ်တစ်ခုကို အကြိမ်ကြိမ် လုပ်ဆောင်ရန် loop များအသုံးပြုပုံ။", "https://www.youtube.com/watch?v=6iF8Xb7Z3wQ", "11:15"),
            ("Functions များ ရေးသားခြင်း", "Code များကို ပြန်လည်အသုံးပြုနိုင်ရန် function များ တည်ဆောက်ပုံ။", "https://www.youtube.com/watch?v=u-OmRn_kjwA", "13:50"),
            ("Object-Oriented Programming (OOP) အခြေခံ", "Classes နှင့် Objects များအကြောင်း မိတ်ဆက်။", "https://www.youtube.com/watch?v=JeznW_7DlB0", "20:00"),
        ]

        for i, (title, content, url, duration) in enumerate(python_lessons, 1):
            Lesson.objects.update_or_create(
                course=course1, order=i,
                defaults={'title': title, 'content': content, 'video_url': url, 'duration': duration}
            )

        # 2. Web Dev Course
        course2, _ = Course.objects.get_or_create(
            title="Modern Web Development with Tailwind CSS",
            defaults={
                'description': "Tailwind CSS ကို အသုံးပြု၍ လှပပြီး responsive ဖြစ်သော website များ တည်ဆောက်ပုံကို လေ့လာပါ။",
                'instructor': admin_user
            }
        )

        web_lessons = [
            ("Introduction to Tailwind CSS", "Tailwind CSS သည် utility-first CSS framework တစ်ခုဖြစ်ပါသည်။", "https://www.youtube.com/watch?v=lCxcTsOHrjo", "12:45"),
            ("Tailwind Utility Classes အခြေခံ", "Margin, Padding, Colors နှင့် Typography များအကြောင်း။", "https://www.youtube.com/watch?v=pfsAzT7SiP8", "15:00"),
            ("Flexbox နှင့် Layout များ", "Flexbox ကို အသုံးပြု၍ website layout ချနည်းများ။", "https://www.youtube.com/watch?v=tI-p9tshSfs", "18:20"),
            ("Grid System တည်ဆောက်ပုံ", "Complex layout များအတွက် CSS Grid အသုံးပြုပုံ။", "https://www.youtube.com/watch?v=h3b9A96v5pM", "14:10"),
            ("Responsive Design ပြုလုပ်ခြင်း", "Mobile, Tablet, Desktop အားလုံးမှာ ကြည့်ကောင်းအောင် ပြုလုပ်ပုံ။", "https://www.youtube.com/watch?v=00gyktocE9k", "16:45"),
            ("Hover, Focus နှင့် အခြား States များ", "Interactive ဖြစ်သော element များ တည်ဆောက်ပုံ။", "https://www.youtube.com/watch?v=p4vI_57yvYQ", "11:30"),
            ("Tailwind Configuration", "မိမိစိတ်ကြိုက် colors နှင့် fonts များ ထည့်သွင်းပုံ။", "https://www.youtube.com/watch?v=sOnBCS3_m_M", "13:20"),
        ]

        for i, (title, content, url, duration) in enumerate(web_lessons, 1):
            Lesson.objects.update_or_create(
                course=course2, order=i,
                defaults={'title': title, 'content': content, 'video_url': url, 'duration': duration}
            )

        self.stdout.write(self.style.SUCCESS("Lessons updated/created successfully!"))
