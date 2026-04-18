from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/change-password/', views.change_password, name='change_password'),

    path('tests/', views.test_list, name='test_list'),
    path('test/<int:test_id>/', views.take_test, name='take_test'),
    path('tests/history/', views.test_history, name='test_history'),

    path('manager/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/tests/', views.manager_tests, name='manager_tests'),
    path('manager/tests/create/', views.manager_test_create, name='manager_test_create'),
    path('manager/tests/<int:test_id>/delete/', views.manager_test_delete, name='manager_test_delete'),
    path('manager/tests/<int:test_id>/edit/', views.manager_test_edit, name='manager_test_edit'),
    path('manager/tests/<int:test_id>/questions/', views.manager_questions, name='manager_questions'),
    path('manager/tests/<int:test_id>/questions/create/', views.manager_question_create, name='manager_question_create'),
    path('manager/questions/<int:question_id>/delete/', views.manager_question_delete, name='manager_question_delete'),
    path('manager/questions/<int:question_id>/edit/', views.manager_question_edit, name='manager_question_edit'),
    path('manager/questions/<int:question_id>/answers/', views.manager_answers, name='manager_answers'),
    path('manager/answers/<int:question_id>/create/', views.manager_answer_create, name='manager_answer_create'),
    path('manager/answers/<int:answer_id>/delete/', views.manager_answer_delete, name='manager_answer_delete'),
    path('manager/answers/<int:answer_id>/edit/', views.manager_answer_edit, name='manager_answer_edit'),
    path('manager/tests/<int:test_id>/publish/', views.manager_test_publish, name='manager_test_publish'),
    path('manager/tests/<int:test_id>/unpublish/', views.manager_test_unpublish, name='manager_test_unpublish'),
    path('manager/assignments/', views.manager_assignments, name='manager_assignments'),
    path('manager/results/', views.manager_results, name='manager_results'),


]