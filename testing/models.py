from email.policy import default
from django.contrib.auth.models import User
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


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
    pass_percent = models.IntegerField(
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Проходной балл (%)"
    )
    is_published = models.BooleanField(default=False, db_index=True, verbose_name="Опубликован")
    target_position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True, db_index=True,
                                        verbose_name="Целевая должность")
    time_limit = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],  # ДОБАВЛЕНО
        help_text="Время в минутах (0 - без ограничений)",
        verbose_name="Лимит времени"
    )
    max_attempts = models.IntegerField(
        default=1,
        validators=[MinValueValidator(0)],  # ДОБАВЛЕНО
        help_text="Максимальное количество попыток (0 - без ограничений)",
        verbose_name="Макс. попыток"
    )

    def __str__(self):
        return self.name

    def get_questions(self):
        return self.questions.all()

    def get_questions_count(self):
        return self.questions.count()

    def has_min_questions(self, min_count=3):
        return self.questions.count() >= min_count


    def can_be_taken_by(self, employee):
        """Проверка, может ли сотрудник пройти тест"""
        if self.max_attempts == 0:
            return True
        attempts = TestAssignment.objects.filter(
            test=self,
            employee=employee,
            is_completed=True
        ).count()
        return attempts < self.max_attempts


    def get_completed_attempts_count(self, employee):
        """Количество успешных попыток сотрудника"""
        return TestAssignment.objects.filter(
            test=self,
            employee=employee,
            is_completed=True
        ).count()


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
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True, db_index=True,
                                 verbose_name="Должность")  # ДОБАВЛЕН db_index

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    def get_assigned_tests(self):
        """Получение назначенных тестов (без циркулярного импорта)"""
        from django.db.models import Q
        # Получаем тесты из прямых назначений и по должности
        return Test.objects.filter(
            Q(testassignment__employee=self) | Q(target_position=self.position),
            is_published=True
        ).distinct()

    def has_completed_test(self, test):
        """Проверка, пройден ли тест (оптимизированная версия)"""
        return TestAssignment.objects.filter(test=test, employee=self, is_completed=True).exists()


    def get_completed_tests_count(self):
        """Количество пройденных тестов"""
        return self.testassignment_set.filter(is_completed=True).count()


class TestAssignment(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, db_index=True)
    assigned_data = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата прохождения")
    deadline = models.DateTimeField(null=True, blank=True, db_index=True,
                                    verbose_name="Срок прохождения")
    def __str__(self):
        return f"{self.test.name} - {self.employee}"

    def complete(self):
        if not self.is_completed:
            self.is_completed = True
            self.completed_at = timezone.now()
            self.save()

    class Meta:
        indexes = [
            models.Index(fields=['employee', 'is_completed']),
            models.Index(fields=['test', 'employee']),
        ]


class UserAnswer(models.Model):
    attempt_id = models.IntegerField(db_index=True, verbose_name="ID попытки")
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True,
                             verbose_name="Пользователь")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="Вопрос")
    selected_answer = models.ForeignKey(Answer, on_delete=models.CASCADE, null=True, blank=True,
                                        verbose_name="Выбранный ответ")
    is_correct = models.BooleanField(default=False, verbose_name="Правильно")
    answered_at = models.DateTimeField(auto_now_add=True, verbose_name="Время ответа")

    class Meta:
        verbose_name = "Ответ пользователя"
        verbose_name_plural = "Ответы пользователей"
        indexes = [
            models.Index(fields=['attempt_id', 'user']),
            models.Index(fields=['question', 'is_correct']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.question.text[:30]}"


class Category(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название категории")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"


class TestAttempt(models.Model):
    """Попытка прохождения теста"""
    assignment = models.ForeignKey(TestAssignment, on_delete=models.CASCADE, related_name='attempts')
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Время начала")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Время завершения")
    score_percent = models.IntegerField(default=0, verbose_name="Результат в %")
    is_passed = models.BooleanField(default=False, verbose_name="Пройден")

    def __str__(self):
        return f"Попытка {self.id} - {self.assignment.test.name} - {self.assignment.employee.user.username}"

    class Meta:
        verbose_name = "Попытка"
        verbose_name_plural = "Попытки"
        ordering = ['-started_at']
