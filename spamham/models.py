from django.db import models
from django.conf import settings


class Prediction(models.Model):
    FEEDBACK_CHOICES = [
        ('', 'No feedback'),
        ('correct', 'Correct'),
        ('wrong', 'Wrong'),
    ]
    SOURCE_CHOICES = [
        ('single', 'Single check'),
        ('batch', 'CSV batch'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    result = models.CharField(max_length=64)
    accuracy = models.FloatField()
    explanation = models.TextField(blank=True, default='')
    feedback = models.CharField(max_length=16, choices=FEEDBACK_CHOICES, blank=True, default='')
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES, default='single')
    batch_id = models.CharField(max_length=36, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.result} ({self.accuracy}%)'
