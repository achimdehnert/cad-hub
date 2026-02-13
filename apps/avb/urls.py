"""AVB URL configuration."""
from django.urls import path

from . import views

app_name = "avb"

urlpatterns = [
    # Bauprojekte
    path(
        "projects/",
        views.ConstructionProjectListView.as_view(),
        name="project_list",
    ),
    path(
        "project/<uuid:pk>/",
        views.ConstructionProjectDetailView.as_view(),
        name="project_detail",
    ),
    path(
        "project/create/",
        views.ConstructionProjectCreateView.as_view(),
        name="project_create",
    ),
    path(
        "project/<uuid:pk>/edit/",
        views.ConstructionProjectUpdateView.as_view(),
        name="project_edit",
    ),
    # Ausschreibungen
    path(
        "tenders/",
        views.TenderListView.as_view(),
        name="tender_list",
    ),
    path(
        "tender/<uuid:pk>/",
        views.TenderDetailView.as_view(),
        name="tender_detail",
    ),
    path(
        "tender/create/",
        views.TenderCreateView.as_view(),
        name="tender_create",
    ),
    path(
        "tender/<uuid:pk>/publish/",
        views.TenderPublishView.as_view(),
        name="tender_publish",
    ),
    path(
        "tender/<uuid:pk>/comparison/",
        views.PriceComparisonView.as_view(),
        name="price_comparison",
    ),
    path(
        "tender/<uuid:pk>/export/comparison/",
        views.ExportPriceComparisonView.as_view(),
        name="export_price_comparison",
    ),
    path(
        "tender/<uuid:pk>/export/gaeb/",
        views.ExportTenderGAEBView.as_view(),
        name="export_tender_gaeb",
    ),
    path(
        "tender/<uuid:pk>/stats/",
        views.TenderStatsAPIView.as_view(),
        name="tender_stats_api",
    ),
    # Bieter
    path(
        "bidders/",
        views.BidderListView.as_view(),
        name="bidder_list",
    ),
    path(
        "bidder/<uuid:pk>/",
        views.BidderDetailView.as_view(),
        name="bidder_detail",
    ),
    path(
        "bidder/create/",
        views.BidderCreateView.as_view(),
        name="bidder_create",
    ),
    # Angebote
    path(
        "tender/<uuid:tender_id>/bids/",
        views.BidListView.as_view(),
        name="bid_list",
    ),
    path(
        "bid/<uuid:pk>/",
        views.BidDetailView.as_view(),
        name="bid_detail",
    ),
    path(
        "tender/<uuid:tender_id>/bid/invite/",
        views.BidCreateView.as_view(),
        name="bid_invite",
    ),
    path(
        "bid/<uuid:pk>/receive/",
        views.BidReceiveView.as_view(),
        name="bid_receive",
    ),
    # Vergabe
    path(
        "tender/<uuid:tender_id>/bid/<uuid:bid_id>/award/",
        views.AwardCreateView.as_view(),
        name="award_create",
    ),
]
