from django.contrib import admin
from .models import Test, Question, Answer, Employee, TestAssignment, Category, Position

admin.site.register(Test)
admin.site.register(Position)
admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(Employee)
admin.site.register(TestAssignment)
admin.site.register(Category)
# Register your models here.
