from django.urls import path

from player.views import PlaybackView


urlpatterns = [
    path(PlaybackView.url, PlaybackView.as_view()),
]
