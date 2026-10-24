"""
Runtime compatibility shims.

Python 3.14 no longer allows setting attributes on ``super()`` proxies, which
breaks ``BaseContext.__copy__`` shipped with Django < 6.0::

    duplicate = copy(super())
    duplicate.dicts = self.dicts[:]   # AttributeError: 'super' object has no attribute 'dicts'

Any template tag that copies the render context (inclusion tags such as
``{% tailwind_css %}``, ``{% include ... only %}``, ...) then raises that
AttributeError — which breaks the whole Django admin and every
``registration/*.html`` page.

The replacement below is the implementation Django ships from 6.0 onwards.
"""

from copy import copy

from django.template.context import BaseContext


def _base_context_copy(self):
    duplicate = BaseContext()
    duplicate.__class__ = self.__class__
    duplicate.__dict__ = copy(self.__dict__)
    duplicate.dicts = self.dicts[:]
    return duplicate


try:
    copy(BaseContext())
except Exception:
    BaseContext.__copy__ = _base_context_copy
