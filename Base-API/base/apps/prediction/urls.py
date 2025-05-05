from rest_framework.routers import DefaultRouter
from .views import (
    PredictionsDataGraphAPIView,
    PredictionsDataTableAPIView,
    StateViewSet,
    MarketViewSet,
    PredictionsDataGraphAPIViewNg,
    PredictionsDataTableAPIViewNg,
    StateViewSetNg,
)
from django.urls import path

router = DefaultRouter()
router.register(r"states", StateViewSet, basename="states")

router.register(r"statesng", StateViewSetNg, basename="statesng")
router.register(r"markets", MarketViewSet, basename="markets")

urlpatterns = router.urls + [
    path(
        "predictions/get_data_graph",
        PredictionsDataGraphAPIView.as_view(),
        name="predictions-data-graph",
    ),
    path(
        "predictions/get_data_table",
        PredictionsDataTableAPIView.as_view(),
        name="predictions-data-table",
    ),
    path(
        "predictions/get_data_graph_ng",
        PredictionsDataGraphAPIViewNg.as_view(),
        name="predictions-data-graph-ng",
    ),
    path(
        "predictions/get_data_table_ng",
        PredictionsDataTableAPIViewNg.as_view(),
        name="predictions-data-table-ng",
    ),
]
