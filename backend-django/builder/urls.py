from django.urls import path
from .mcp_views import (
    ChatView,
    SearchComponentsView,
    BottleneckView,
    CompatibilityView,
    BenchmarkView,
    AutoBuildView,
    PreferencesView,
    GenerateImageView,
    AlternativesView,
    ParseBuildFromTextView,
)

urlpatterns = [
    # Chat AI principal (necesită JWT)
    path('chat/', ChatView.as_view(), name='builder-chat'),

    # Endpoint-uri directe (fără AI)
    path('search/', SearchComponentsView.as_view(), name='builder-search'),
    path('bottleneck/', BottleneckView.as_view(), name='builder-bottleneck'),
    path('compatibility/', CompatibilityView.as_view(), name='builder-compatibility'),
    path('benchmark/', BenchmarkView.as_view(), name='builder-benchmark'),
    path('auto-build/', AutoBuildView.as_view(), name='builder-auto-build'),
    path('preferences/', PreferencesView.as_view(), name='builder-preferences'),
    path('generate-image/', GenerateImageView.as_view(), name='builder-generate-image'),
    path('alternatives/', AlternativesView.as_view(), name='builder-alternatives'),
    path('parse-build/', ParseBuildFromTextView.as_view(), name='builder-parse-build'),
]
