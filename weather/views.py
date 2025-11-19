from django.views.generic import TemplateView

from .models import Parameter, Region


class DashboardView(TemplateView):
    template_name = "weather/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        regions = Region.objects.all()
        parameters = Parameter.objects.all()
        context["regions"] = regions
        context["parameters"] = parameters
        context["default_region_code"] = regions.first().code if regions else ""
        context["default_parameter_code"] = parameters.first().code if parameters else ""
        return context
