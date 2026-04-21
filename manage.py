#!/usr/bin/env python
import os
import sys
import pickle
from functools import lru_cache
from utils import text_process


def makePipelineCompatible(pipeline):
    if not hasattr(pipeline, 'transform_input'):
        pipeline.transform_input = None

    for _, step in pipeline.steps:
        if hasattr(step, '_idf_diag') and not hasattr(step, 'idf_'):
            step.idf_ = step._idf_diag.diagonal()
            step.n_features_in_ = step._idf_diag.shape[0]

        if step.__class__.__name__ == 'MultinomialNB':
            if not hasattr(step, 'force_alpha'):
                step.force_alpha = True
            if not hasattr(step, 'n_features_in_') and hasattr(step, 'feature_count_'):
                step.n_features_in_ = step.feature_count_.shape[1]

    return pipeline


@lru_cache(maxsize=1)
def importPipelines():
    pipeline = pickle.load(open('text_clf_pipeline.pkl', 'rb'))
    pipeline_second = pickle.load(open('spam_clf_model_pipeline_final_second.pkl', 'rb'))
    return makePipelineCompatible(pipeline), makePipelineCompatible(pipeline_second)


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "textclassifier.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)
