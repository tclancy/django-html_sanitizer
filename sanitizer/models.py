from django.conf import settings
from django.db import models

import sys
if sys.version_info[0] == 3:
    from django.utils.encoding import smart_text as smart_unicode
else:
    from django.utils.encoding import smart_unicode

import bleach
import html5lib
from html5lib.filters.base import Filter


class NoChildTagFilter(Filter):
    """
    ONLY WORKS ON TAGS THAT CANNOT HAVE CHILDREN
    """
    def __init__(self, stream, tags):
        Filter.__init__(self, stream)
        self._tags = [t.lower() for t in tags]

    def __iter__(self):
        tokens = Filter.__iter__(self)
        while True:
            for token in tokens:
                if token["type"] == "StartTag" and token["name"].lower() in self._tags:
                    break
                yield token
            else:
                # we ran out of tokens
                break
            for token in tokens:
                if token["type"] == "EndTag" and token["name"].lower() in self._tags:
                    break


def strip_style_and_script(input):
    dom = html5lib.parseFragment(input, treebuilder="dom")
    walker = html5lib.getTreeWalker("dom")
    stream = walker(dom)

    s = html5lib.serializer.HTMLSerializer()

    return s.render(NoChildTagFilter(stream, ("script", "style")))


class SanitizedCharField(models.CharField):
    
    def __init__(self, allowed_tags=[], allowed_attributes=[],
                 allowed_styles=[], strip=False, 
                 *args, **kwargs):
        self._sanitizer_allowed_tags = allowed_tags
        self._sanitizer_allowed_attributes = allowed_attributes
        self._sanitizer_allowed_styles = allowed_styles
        self._sanitizer_strip = strip
        super(SanitizedCharField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        value = super(SanitizedCharField, self).to_python(value)
        value = bleach.clean(value, tags=self._sanitizer_allowed_tags,
            attributes=self._sanitizer_allowed_attributes, 
            styles=self._sanitizer_allowed_styles, strip=self._sanitizer_strip,
            strip_comments=self._sanitizer_strip)
        return smart_unicode(value)


class SanitizedTextField(models.TextField):
    
    def __init__(self, allowed_tags=[], allowed_attributes=[], 
                 allowed_styles=[], strip=False, 
                 *args, **kwargs):
        self._sanitizer_allowed_tags = allowed_tags
        self._sanitizer_allowed_attributes = allowed_attributes
        self._sanitizer_allowed_styles = allowed_styles
        self._sanitizer_strip = strip
        super(SanitizedTextField, self).__init__(*args, **kwargs)

    def _clean(self, value):
        value = strip_style_and_script(value)
        return bleach.clean(value, tags=self._sanitizer_allowed_tags,
                            attributes=self._sanitizer_allowed_attributes,
                            styles=self._sanitizer_allowed_styles, strip=self._sanitizer_strip,
                            strip_comments=self._sanitizer_strip)

    def to_python(self, value):
        value = super(SanitizedTextField, self).to_python(value)
        return smart_unicode(self._clean(value))

    def get_prep_value(self, value):
        value = super(SanitizedTextField, self).get_prep_value(value)
        return self._clean(value)


if "south" in settings.INSTALLED_APPS:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^sanitizer\.models\.SanitizedCharField"])
    add_introspection_rules([], ["^sanitizer\.models\.SanitizedTextField"])
