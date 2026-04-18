from .models import Test, Question, Answer, Employee, TestAssignment, UserAnswer
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Count, Q
from .models import UserAnswer, Category, TestAttempt


class TestService:
    @staticmethod
    def calculate_score(test, user_answers):
        questions = test.questions.all()
        score = 0
        total = 0

        for question in questions:
            total += 1
            answer_id = user_answers.get(f'question_{question.id}')
            if answer_id:
                try:
                    answer = Answer.objects.get(id=answer_id)
                    if answer.is_correct:
                        score += 1
                except Answer.DoesNotExist:
                    pass

        return int((score / total) * 100) if total > 0 else 0

    @staticmethod
    def complete_assignment(employee, test, percent, pass_percent):
        if percent >= pass_percent:
            try:
                assignment = TestAssignment.objects.get(test=test, employee=employee)
                if not assignment.is_completed:
                    assignment.is_completed = True
                    assignment.completed_at = timezone.now()
                    assignment.save()
                    return True
            except TestAssignment.DoesNotExist:
                pass
        return False

    @staticmethod
    def create_attempt(assignment):
        return TestAttempt.objects.create(assignment=assignment)

    @staticmethod
    def complete_attempt(attempt, score_percent, is_passed):
        attempt.completed_at = timezone.now()
        attempt.score_percent = score_percent
        attempt.is_passed = is_passed
        attempt.save()
        return attempt

    @staticmethod
    def get_attempts_count(employee, test):
        return TestAttempt.objects.filter(
            assignment__employee=employee,
            assignment__test=test
        ).count()


    @staticmethod
    def get_remaining_attempts(employee, test):
        if test.max_attempts == 0:
            return float('inf')
        attempts_count = TestService.get_attempts_count(employee, test)
        return max(0, test.max_attempts - attempts_count)


    @staticmethod
    def can_take_test(employee, test):
        if test.max_attempts == 0:
            return True
        attempts_count = TestService.get_attempts_count(employee, test)
        return attempts_count < test.max_attempts

class EmployeeService:
    @staticmethod
    def get_employee_by_user(user):
        try:
            return Employee.objects.select_related('position').get(user=user)
        except Employee.DoesNotExist:
            return None

    @staticmethod
    def get_assigned_tests(employee):

        if not employee:
            return Test.objects.none()


        return Test.objects.filter(
            Q(testassignment__employee=employee) | Q(target_position=employee.position),
            is_published=True
        ).distinct().select_related('category', 'target_position')

    @staticmethod
    def get_assignment(employee, test):

        return TestAssignment.objects.filter(test=test, employee=employee).select_related('test').first()


class ManagerService:
    @staticmethod
    def get_dashboard_stats():
        return {
            'tests_count': Test.objects.count(),
            'questions_count': Question.objects.count(),
            'assignments_count': TestAssignment.objects.count(),
            'categories_count': Category.objects.count(),
        }


class AnswerService:
    @staticmethod
    def save_user_answers(user, test, user_answers_dict, attempt):

        for question_id_str, answer_id in user_answers_dict.items():
            if not answer_id:
                continue

            try:
                question_id = int(question_id_str.replace('question_', ''))
                question = Question.objects.get(id=question_id)
                answer = Answer.objects.get(id=answer_id)

                is_correct = answer.is_correct

                UserAnswer.objects.create(
                    attempt_id=attempt.id,
                    user=user,
                    question=question,
                    selected_answer=answer,
                    is_correct=is_correct
                )
            except (Question.DoesNotExist, Answer.DoesNotExist, ValueError):
                continue

    @staticmethod
    def get_user_answers_for_attempt(attempt_id):
        return UserAnswer.objects.filter(attempt_id=attempt_id).select_related(
            'question', 'selected_answer'
        )

    @staticmethod
    def get_user_answers_for_attempt_with_details(attempt_id):
        return UserAnswer.objects.filter(attempt_id=attempt_id).select_related(
            'question', 'selected_answer', 'question__test'
        )

    @staticmethod
    def create_attempt(assignment):
        return TestAttempt.objects.create(assignment=assignment)

    @staticmethod
    def complete_attempt(attempt, score_percent, is_passed):
        attempt.completed_at = timezone.now()
        attempt.score_percent = score_percent
        attempt.is_passed = is_passed
        attempt.save()
        return attempt

    @staticmethod
    def get_attempts_count(employee, test):
        return TestAttempt.objects.filter(
            assignment__employee=employee,
            assignment__test=test
        ).count()

    @staticmethod
    def get_remaining_attempts(employee, test):
        if test.max_attempts == 0:
            return float('inf')  # Без ограничений
        attempts_count = TestService.get_attempts_count(employee, test)
        return max(0, test.max_attempts - attempts_count)

    @staticmethod
    def can_take_test(employee, test):
        if test.max_attempts == 0:
            return True
        attempts_count = TestService.get_attempts_count(employee, test)
        return attempts_count < test.max_attempts