from email.policy import default
from django.contrib.auth.models import User
from django.db import models

# Create your models here.

class Position(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="Название должности")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Должность"
        verbose_name_plural = "Должности"

class Test(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Категория")
    pass_percent = models.IntegerField(default=70, verbose_name="Проходной балл (%)")
    is_published = models.BooleanField(default=False, verbose_name="Опубликован")
    target_position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Целевая должность")
    time_limit = models.IntegerField(default=0, help_text="Время в минутах (0 - без ограничений)",verbose_name="Лимит времени")
    max_attempts = models.IntegerField(default=1, help_text="Максимальное количество попыток (0 - без ограничений)", verbose_name="Макс. попыток")

    def __str__(self):
        return self.name

    def get_questions(self):
        return self.questions.all()

    def get_questions_count(self):
        return self.questions.count()

    def has_min_questions(self, min_count=3):
        return self.questions.count() >= min_count


class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=500)

    def __str__(self):
        return self.text

    def get_answers(self):
        return self.answers.all()

    def get_correct_answer(self):
        correct = self.answers.filter(is_correct=True).first()
        return correct


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.CharField(max_length=200, blank=True, verbose_name="Отдел")
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Должность")

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    def get_assigned_tests(self):
        from .services import EmployeeService
        return EmployeeService.get_assigned_tests(self)

    def has_completed_test(self, test):
        from .models import TestAssignment
        try:
            assignment = TestAssignment.objects.get(test=test, employee=self)
            return assignment.is_completed
        except TestAssignment.DoesNotExist:
            return False




class TestAssignment(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    assigned_data = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата прохождения")
    deadline = models.DateTimeField(null=True, blank=True, verbose_name="Срок прохождения")

    def __str__(self):
        return f"{self.test.name} - {self.employee}"

    def complete(self):
        if not self.is_completed:
            self.is_completed = True
            self.save()


class UserAnswer(models.Model):
    attempt_id = models.IntegerField(verbose_name="ID попытки")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="Вопрос")
    selected_answer = models.ForeignKey(Answer, on_delete=models.CASCADE, null=True, blank=True,
                                        verbose_name="Выбранный ответ")
    is_correct = models.BooleanField(default=False, verbose_name="Правильно")
    answered_at = models.DateTimeField(auto_now_add=True, verbose_name="Время ответа")

    class Meta:
        verbose_name = "Ответ пользователя"
        verbose_name_plural = "Ответы пользователей"

    def __str__(self):
        return f"{self.user.username} - {self.question.text[:30]}"


class Category(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название категории")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"