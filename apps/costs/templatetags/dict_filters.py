from django import template

register = template.Library()

@register.filter
def dict_get(d, key):
    try:
        return d[key]
    except (KeyError, TypeError):
        return None