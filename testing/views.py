from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.utils import timezone
from .models import Test, Question, Answer, Employee, TestAssignment, Category, Position, TestAttempt
from .services import TestService, EmployeeService, ManagerService
from .constants import MSG_LOGIN_ERROR


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if user.is_staff:
                return redirect('manager_dashboard')
            else:
                return redirect('test_list')
        else:
            return render(request, 'registration/login.html', {'error': MSG_LOGIN_ERROR})

    return render(request, 'registration/login.html')


def logout_view(request):
    logout(request)
    return redirect('/')


@login_required
def test_list(request):
    employee = EmployeeService.get_employee_by_user(request.user)
    tests = EmployeeService.get_assigned_tests(employee)


    for test in tests:
        test.remaining_attempts = TestService.get_remaining_attempts(employee, test)
        test.can_take = TestService.can_take_test(employee, test)
    now = timezone.now()
    return render(request, 'testing/test_list.html', {'tests': tests, 'now': now })


@login_required
def take_test(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    questions = test.get_questions()

    employee = EmployeeService.get_employee_by_user(request.user)
    assignment = EmployeeService.get_assignment(employee, test)

    # Проверка: можно ли пройти тест (не превышены ли попытки)
    if not TestService.can_take_test(employee, test):
        return render(request, 'testing/error.html', {
            'message': f'Вы исчерпали лимит попыток для теста «{test.name}». Максимум: {test.max_attempts} попыт(ок/и).'
        })

    if request.method == 'POST':
        from .services import AnswerService

        attempt = TestService.create_attempt(assignment)

        AnswerService.save_user_answers(request.user, test, request.POST, attempt)

        percent = TestService.calculate_score(test, request.POST)
        is_passed = percent >= test.pass_percent

        TestService.complete_attempt(attempt, percent, is_passed)


        if assignment and is_passed:
            assignment.is_completed = True
            assignment.completed_at = timezone.now()
            assignment.save()

        # Получаем детальные ответы
        user_answers = AnswerService.get_user_answers_for_attempt(attempt.id)

        questions_data = []
        for question in questions:
            user_answer = user_answers.filter(question=question).first()
            correct_answer = question.get_correct_answer()

            questions_data.append({
                'text': question.text,
                'user_answer_text': user_answer.selected_answer.text if user_answer and user_answer.selected_answer else 'Не выбран',
                'correct_answer_text': correct_answer.text if correct_answer else 'Нет ответа',
                'is_correct': user_answer.is_correct if user_answer else False,
            })

        return render(request, 'testing/result.html', {
            'test': test,
            'percent': percent,
            'questions_data': questions_data,
        })

    return render(request, 'testing/take_test.html', {
        'test': test,
        'questions': questions
    })


@staff_member_required
def manager_dashboard(request):
    stats = ManagerService.get_dashboard_stats()
    return render(request, 'testing/manager/dashboard.html', stats)


@staff_member_required
def manager_tests(request):
    tests = Test.objects.all().order_by('-id')
    categories = Category.objects.all()
    return render(request, 'testing/manager/tests.html', {'tests': tests})


@staff_member_required
def manager_test_create(request):
    categories = Category.objects.all()
    positions = Position.objects.all()
    if request.method == 'POST':
        name = request.POST.get('name')
        category_id = request.POST.get('category_id')
        pass_percent = request.POST.get('pass_percent', 70)
        time_limit = request.POST.get('time_limit', 0)
        max_attempts = request.POST.get('max_attempts', 1)
        test = Test.objects.create(name=name, pass_percent=pass_percent)
        test.time_limit = time_limit
        test.max_attempts = max_attempts

        if category_id:
            try:
                category = Category.objects.get(id=category_id)
                test.category = category
                test.save()
            except Category.DoesNotExist:
                pass

        return redirect('manager_tests')

    return render(request, 'testing/manager/test_form.html', {'categories': categories, 'positions': positions})


@staff_member_required
def manager_test_delete(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    test.delete()
    return redirect('manager_tests')


@staff_member_required
def manager_questions(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    questions = test.questions.all()
    return render(request, 'testing/manager/questions.html', {'test': test, 'questions': questions})


@staff_member_required
def manager_question_create(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if request.method == 'POST':
        text = request.POST.get('text')
        Question.objects.create(test=test, text=text)
        return redirect('manager_questions', test_id=test.id)
    return render(request, 'testing/manager/question_form.html', {'test': test})


@staff_member_required
def manager_question_delete(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    test_id = question.test.id
    question.delete()
    return redirect('manager_questions', test_id=test_id)


@staff_member_required
def manager_answers(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    answers = question.answers.all()
    return render(request, 'testing/manager/answers.html', {'question': question, 'answers': answers})


@staff_member_required
def manager_answer_create(request, question_id):
    question = get_object_or_404(Question, id=question_id)

    if request.method == 'POST':
        text = request.POST.get('text')
        is_correct = request.POST.get('is_correct') == 'on'
        Answer.objects.create(
            question=question,
            text=text,
            is_correct=is_correct
        )
        return redirect('manager_answers', question_id=question.id)

    return render(request, 'testing/manager/answer_form.html', {'question': question})


@staff_member_required
def manager_answer_delete(request, answer_id):
    answer = get_object_or_404(Answer, id=answer_id)
    question_id = answer.question.id
    answer.delete()
    return redirect('manager_answers', question_id=question_id)


@staff_member_required
def manager_assignments(request):
    employees = Employee.objects.all()
    tests = Test.objects.all()
    assignments = TestAssignment.objects.all().order_by('-assigned_data')
    positions = Position.objects.all()

    error_message = None
    success_message = None

    if request.method == 'POST':
        action = request.POST.get('action')
        test_id = request.POST.get('test_id')

        try:
            test = Test.objects.get(id=test_id)
        except Test.DoesNotExist:
            error_message = "Тест не найден"
            return render(request, 'testing/manager/assignments.html', {
                'employees': employees,
                'tests': tests,
                'assignments': assignments,
                'positions': positions,
                'error_message': error_message,
            })

        if not test.has_min_questions(3):
            error_message = f"Тест «{test.name}» содержит только {test.get_questions_count()} вопрос(ов). Для назначения необходимо минимум 3 вопроса."
            return render(request, 'testing/manager/assignments.html', {
                'employees': employees,
                'tests': tests,
                'assignments': assignments,
                'positions': positions,
                'error_message': error_message,
            })

        if action == 'single':
            employee_id = request.POST.get('employee_id')
            if employee_id and test_id:
                TestAssignment.objects.create(
                    test_id=test_id,
                    employee_id=employee_id
                )
                success_message = "Тест успешно назначен сотруднику"

        elif action == 'mass':
            position_id = request.POST.get('position_id')
            if position_id and test_id:
                employees_in_position = Employee.objects.filter(position_id=position_id)
                count = 0
                for emp in employees_in_position:
                    obj, created = TestAssignment.objects.get_or_create(
                        test_id=test_id,
                        employee=emp
                    )
                    if created:
                        count += 1
                success_message = f"Тест назначен {count} сотрудникам"

        return redirect('manager_assignments')

    context = {
        'employees': employees,
        'tests': tests,
        'assignments': assignments,
        'positions': positions,
        'error_message': error_message,
        'success_message': success_message,
    }
    return render(request, 'testing/manager/assignments.html', context)


@staff_member_required
def manager_results(request):
    assignments = TestAssignment.objects.filter(is_completed=True).order_by('-assigned_data')
    return render(request, 'testing/manager/results.html', {'assignments': assignments})


@staff_member_required
def manager_test_edit(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    categories = Category.objects.all()

    if request.method == 'POST':
        test.name = request.POST.get('name')
        test.pass_percent = request.POST.get('pass_percent', 70)
        category_id = request.POST.get('category_id')

        if category_id:
            try:
                test.category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                pass
        else:
            test.category = None

        test.save()
        return redirect('manager_tests')

    return render(request, 'testing/manager/test_edit.html', {
        'test': test,
        'categories': categories
    })


@staff_member_required
def manager_question_edit(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    test = question.test

    if request.method == 'POST':
        question.text = request.POST.get('text')
        question.save()
        return redirect('manager_questions', test_id=test.id)

    return render(request, 'testing/manager/question_edit.html', {
        'question': question,
        'test': test
    })


@staff_member_required
def manager_answer_edit(request, answer_id):
    answer = get_object_or_404(Answer, id=answer_id)
    question = answer.question

    if request.method == 'POST':
        answer.text = request.POST.get('text')
        answer.is_correct = request.POST.get('is_correct') == 'on'
        answer.save()
        return redirect('manager_answers', question_id=question.id)

    return render(request, 'testing/manager/answer_edit.html', {
        'answer': answer,
        'question': question
    })

@staff_member_required
def manager_test_publish(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    test.is_published = True
    test.save()
    return redirect('manager_tests')

@staff_member_required
def manager_test_unpublish(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    test.is_published = False
    test.save()
    return redirect('manager_tests')


@login_required
def profile(request):
    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        employee = None

    context = {
        'user': request.user,
        'employee': employee,
    }
    return render(request, 'testing/profile.html', context)


@login_required
def profile_edit(request):
    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        employee = None

    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()

        if employee:
            employee.phone = request.POST.get('phone', '')
            employee.save()

        return redirect('profile')

    context = {
        'user': request.user,
        'employee': employee,
    }
    return render(request, 'testing/profile_edit.html', context)


@login_required
def change_password(request):

    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            return redirect('profile')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'testing/change_password.html', {'form': form})


@staff_member_required
def manager_tests(request):
    tests = Test.objects.all().order_by('-id')

    category_id = request.GET.get('category')
    if category_id and category_id != 'all':
        tests = tests.filter(category_id=category_id)

    status = request.GET.get('status')
    if status == 'published':
        tests = tests.filter(is_published=True)
    elif status == 'draft':
        tests = tests.filter(is_published=False)

    search = request.GET.get('search')
    if search:
        tests = tests.filter(name__icontains=search)

    categories = Category.objects.all().order_by('name')

    context = {
        'tests': tests,
        'categories': categories,
        'filter_category': category_id or 'all',
        'filter_status': status or 'all',
        'search_query': search or '',
    }
    return render(request, 'testing/manager/tests.html', context)


@login_required
def test_history(request):
    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        employee = None

    if employee:
        completed_assignments = TestAssignment.objects.filter(
            employee=employee,
            is_completed=True
        ).order_by('-completed_at').select_related('test')

        history = []
        for assignment in completed_assignments:
            from .models import UserAnswer
            user_answers = UserAnswer.objects.filter(
                user=request.user,
                question__test=assignment.test
            )

            correct_count = user_answers.filter(is_correct=True).count()
            total_count = user_answers.count()
            percent = int((correct_count / total_count) * 100) if total_count > 0 else 0

            history.append({
                'test_name': assignment.test.name,
                'completed_at': assignment.completed_at,
                'percent': percent,
                'correct_count': correct_count,
                'total_count': total_count,
            })
    else:
        history = []

    return render(request, 'testing/test_history.html', {'history': history})