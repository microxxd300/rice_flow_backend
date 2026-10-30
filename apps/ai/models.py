from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.db import models

# About 10 pages. It goes into every chat request, so it has to stay small.
MAX_KNOWLEDGE_CHARS = 20000


class KnowledgeSheet(models.Model):
    """
    Singleton holding the rice-farming reference the AI chat answers from: practices
    written up by RiceFlow's agriculturists from PhilRice and DA sources, each part
    naming its source. The admin website edits it through GET/PUT /api/ai/knowledge/;
    it can also be edited in Django admin. Empty means the chat uses general knowledge.
    """
    content    = models.TextField(blank=True, default='', validators=[MaxLengthValidator(MAX_KNOWLEDGE_CHARS)])
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        verbose_name        = 'AI knowledge sheet'
        verbose_name_plural = 'AI knowledge sheet'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def current(cls) -> 'KnowledgeSheet':
        return cls.objects.get_or_create(pk=1)[0]

    def __str__(self):
        return f"AI knowledge sheet · {len(self.content)} characters"
