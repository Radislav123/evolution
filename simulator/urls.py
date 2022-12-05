from django.urls import path

from simulator.views import SimulationView


urlpatterns = [
    path(SimulationView.url, SimulationView.as_view()),
]
