from django import template

register = template.Library()

@register.filter
def modulo(num, val):
    return num % val