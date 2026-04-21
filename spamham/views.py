import csv
import io
import math
import uuid

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Avg, Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from manage import importPipelines
from utils import text_process
from .models import Prediction


def history_for(request):
    queryset = Prediction.objects.all()
    if request.user.is_authenticated:
        return queryset.filter(user=request.user)[:10]
    return queryset.filter(user__isnull=True)[:10]


def create_prediction(request, message, source='single', batch_id=''):
    processed_message = [' '.join(text_process([message]))]
    result, accuracy, explanation = predict(processed_message)
    return Prediction.objects.create(
        user=request.user if request.user.is_authenticated else None,
        message=message,
        result=result,
        accuracy=accuracy,
        explanation=explanation,
        source=source,
        batch_id=batch_id,
    )


def home(request):
    context = {
        'history': history_for(request),
        'batch_results': [],
    }

    if request.method == 'POST':
        prediction = create_prediction(request, request.POST.get('message', ''))
        context.update({
            'result': prediction.result,
            'message': prediction.message,
            'accuracy': prediction.accuracy,
            'explanation': prediction.explanation,
            'prediction': prediction,
            'history': history_for(request),
        })

    return render(request, 'home.html', context)


def batch_upload(request):
    if request.method != 'POST':
        return redirect('home')

    upload = request.FILES.get('csv_file')
    if not upload:
        return redirect('home')

    batch_id = str(uuid.uuid4())
    content = upload.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)

    if reader.fieldnames and 'message' in [name.lower() for name in reader.fieldnames]:
        message_field = next(name for name in reader.fieldnames if name.lower() == 'message')
        messages = [row.get(message_field, '').strip() for row in rows]
    else:
        raw_rows = csv.reader(io.StringIO(content))
        messages = [row[0].strip() for row in raw_rows if row]
        if messages and messages[0].lower() == 'message':
            messages = messages[1:]

    predictions = [
        create_prediction(request, message, source='batch', batch_id=batch_id)
        for message in messages
        if message
    ]

    return render(request, 'home.html', {
        'history': history_for(request),
        'batch_results': predictions,
        'batch_id': batch_id,
    })


def batch_download(request, batch_id):
    predictions = Prediction.objects.filter(batch_id=batch_id, source='batch')
    if request.user.is_authenticated:
        predictions = predictions.filter(user=request.user)
    else:
        predictions = predictions.filter(user__isnull=True)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="spamham-batch-{batch_id}.csv"'
    writer = csv.writer(response)
    writer.writerow(['message', 'result', 'accuracy', 'explanation'])
    for prediction in predictions:
        writer.writerow([prediction.message, prediction.result, prediction.accuracy, prediction.explanation])
    return response


def feedback(request, prediction_id):
    if request.method == 'POST':
        queryset = Prediction.objects.all()
        if request.user.is_authenticated:
            queryset = queryset.filter(user=request.user)
        else:
            queryset = queryset.filter(user__isnull=True)

        prediction = get_object_or_404(queryset, pk=prediction_id)
        feedback_value = request.POST.get('feedback', '')
        if feedback_value in ('correct', 'wrong'):
            prediction.feedback = feedback_value
            prediction.save(update_fields=['feedback', 'updated_at'])

    return redirect('home')


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()

    return render(request, 'registration/register.html', {'form': form})


@staff_member_required
def analytics(request):
    totals = Prediction.objects.aggregate(
        total=Count('id'),
        single=Count('id', filter=Q(source='single')),
        batch=Count('id', filter=Q(source='batch')),
        correct=Count('id', filter=Q(feedback='correct')),
        wrong=Count('id', filter=Q(feedback='wrong')),
        average_accuracy=Avg('accuracy'),
    )
    recent = Prediction.objects.all()[:20]
    by_result = Prediction.objects.values('result').annotate(total=Count('id')).order_by('-total')

    return render(request, 'analytics.html', {
        'totals': totals,
        'recent': recent,
        'by_result': by_result,
    })


def explain_message(message, result, first_prob, second_prob):
    tokens = text_process(message)
    pipeline, pipeline_second = importPipelines()
    vocabularies = []

    for pipeline_item in (pipeline, pipeline_second):
        vectorizer = pipeline_item.named_steps.get('email_tfidf')
        if vectorizer is not None and hasattr(vectorizer, 'vocabulary_'):
            vocabularies.append(vectorizer.vocabulary_)

    signals = []
    for token in tokens:
        if any(token in vocabulary for vocabulary in vocabularies) and token.lower() not in signals:
            signals.append(token.lower())

    probability_gap = abs(float(first_prob[0][1]) - float(second_prob[0][1]))
    signal_text = ', '.join(signals[:8]) if signals else 'No strong trained-vocabulary terms were found.'
    return (
        f'Signals: {signal_text}. '
        f'Model spam probabilities were {round(float(first_prob[0][1]) * 100, 1)}% '
        f'and {round(float(second_prob[0][1]) * 100, 1)}%; agreement gap {round(probability_gap * 100, 1)}%.'
    )


def predict(message):
    result = " "

    pipeline, pipeline_second = importPipelines()

    test_prob = pipeline.predict_proba(message)
    test_second_prob = pipeline_second.predict_proba(message)

    value_spam = test_prob[0][1]
    value_spam_second = test_second_prob[0][1]

    value_ham = test_prob[0][0]
    value_ham_second = test_second_prob[0][0]

    if value_spam > 0.5 and value_spam_second > 0.5:
        result = 'spam'
        accuracy = max(value_spam, value_spam_second)
    elif value_spam <= 0.5 and value_spam_second <= 0.5:
        result = 'ham'
        accuracy = max(value_ham, value_ham_second)
    elif value_spam > 0.5 or value_spam_second > 0.5:
        if max(value_spam, value_spam_second) + 0.1 > max(value_ham, value_ham_second):
            accuracy = max(value_spam, value_spam_second)
            result = 'spam'
        else:
            result = 'ham'
            accuracy = max(value_ham, value_ham_second)
    else:
        result = 'ham'
        accuracy = max(value_ham, value_ham_second)

    accuracy = round(accuracy, 3) * 100

    if result == 'spam':
        result = 'very likely a spam' if accuracy > 80 else 'less likely a spam'
    else:
        result = 'very likely a ham' if accuracy > 80 else 'less likely a ham'

    return result, accuracy, explain_message(message, result, test_prob, test_second_prob)
