from django.shortcuts import render, redirect


def render_with_error(request, template, error_message, context=None):
    if context is None:
        context = {}
    context['error'] = error_message
    return render(request, template, context)