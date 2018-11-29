import uuid

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import redirect
from django.views.generic import TemplateView, ListView, \
    DetailView, CreateView, UpdateView
from django.views.generic.detail import BaseDetailView

from .models import Ambulance, AmbulanceCapability, AmbulanceStatus, \
    Call, Location, LocationType, CallStatus, AmbulanceCallStatus, \
    CallPriority, AmbulanceStatusOrder, AmbulanceCapabilityOrder, CallStatusOrder, CallPriorityOrder, LocationTypeOrder

from .forms import AmbulanceCreateForm, AmbulanceUpdateForm, LocationAdminCreateForm, LocationAdminUpdateForm

from emstrack.mixins import BasePermissionMixin, UpdatedByMixin

from emstrack.views import get_page_links, get_page_size_links


# Ambulance views

class AmbulancePermissionMixin(BasePermissionMixin):

    filter_field = 'id'
    profile_field = 'ambulances'
    queryset = Ambulance.objects.all()


class AmbulanceDetailView(LoginRequiredMixin,
                          SuccessMessageMixin,
                          UpdatedByMixin,
                          AmbulancePermissionMixin,
                          DetailView):

    model = Ambulance
    
    def get_context_data(self, **kwargs):

        # add paginated updates to context

        # call supper
        context = super().get_context_data(**kwargs)

        # query
        updates_query = self.object.ambulanceupdate_set.order_by('-timestamp')

        # get current page
        page = self.request.GET.get('page', 1)
        page_size = self.request.GET.get('page_size', 250)
        page_sizes = [250, 500, 1000]

        # paginate
        paginator = Paginator(updates_query, page_size)
        try:
            updates = paginator.page(page)
        except PageNotAnInteger:
            updates = paginator.page(1)
        except EmptyPage:
            updates = paginator.page(paginator.num_pages)

        context['updates'] = updates
        context['page_links'] = get_page_links(self.request, updates)
        context['page_size_links'] = get_page_size_links(self.request, updates, page_sizes)
        context['page_size'] = int(page_size)

        # add ambulance_status
        context['ambulance_status'] = {m.name: m.value
                                       for m in AmbulanceStatus}

        return context


class AmbulanceListView(LoginRequiredMixin,
                        AmbulancePermissionMixin,
                        ListView):
    
    model = Ambulance
    ordering = ['identifier']


class AmbulanceCreateView(LoginRequiredMixin,
                          SuccessMessageMixin,
                          UpdatedByMixin,
                          AmbulancePermissionMixin,
                          CreateView):
    
    model = Ambulance
    form_class = AmbulanceCreateForm

    def get_success_url(self):
        return self.object.get_absolute_url()
    

class AmbulanceUpdateView(LoginRequiredMixin,
                          SuccessMessageMixin,
                          UpdatedByMixin,
                          AmbulancePermissionMixin,
                          UpdateView):
    
    model = Ambulance
    form_class = AmbulanceUpdateForm

    def get_success_url(self):
        return self.object.get_absolute_url()


# Ambulance css information
AmbulanceCSS = {

    'UK': {
        'icon': {
            'iconUrl': '/static/icons/cars/ambulance_blue.svg',
            'iconSize': [15, 30],
        },
        'class': 'primary'
    },
    'AV': {
        'icon': {
            'iconUrl': '/static/icons/cars/ambulance_green.svg',
            'iconSize': [15, 30],
        },
        'class': 'success'
    },
    'OS': {
        'icon': {
            'iconUrl': '/static/icons/cars/ambulance_gray.svg',
            'iconSize': [15, 30],
        },
        'class': 'secondary'
    },

    'PB': {
        'icon': {
            'iconUrl': '/static/icons/cars/ambulance_red.svg',
            'iconSize': [15, 30],
        },
        'class': 'danger'
    },
    'AP': {
        'icon': {
            'iconUrl': '/static/icons/cars/ambulance_orange.svg',
            'iconSize': [15, 30],
        },
        'class': 'warning'
    },

    'HB': {
        'icon': {
            'iconUrl': '/static/icons/cars/ambulance_red.svg',
            'iconSize': [15, 30],
        },
        'class': 'danger'
    },
    'AH': {
        'icon': {
            'iconUrl': '/static/icons/cars/ambulance_orange.svg',
            'iconSize': [15, 30],
        },
        'class': 'warning'
    },

    'BB': {
        'icon': {
            'iconUrl': '/static/icons/cars/ambulance_red.svg',
            'iconSize': [15, 30],
        },
        'class': 'danger'
    },
    'AB': {
        'icon': {
            'iconUrl': '/static/icons/cars/ambulance_orange.svg',
            'iconSize': [15, 30],
        },
        'class': 'warning'
    },


    'WB': {
        'icon': {
            'iconUrl': '/static/icons/cars/ambulance_red.svg',
            'iconSize': [15, 30],
        },
        'class': 'danger'
    },
    'AW': {
        'icon': {
            'iconUrl': '/static/icons/cars/ambulance_orange.svg',
            'iconSize': [15, 30],
        },
        'class': 'warning'
    }

}


# CallPriority css information
CallPriorityCSS = {
    'A': {
        'class': 'success',
        'html': 'A'
    },
    'B': {
        'class': 'yellow',
        'html': 'B'
    },
    'C': {
        'class': 'warning',
        'html': 'C'
    },
    'D': {
        'class': 'danger',
        'html': 'D'
    },
    'E': {
        'class': 'info',
        'html': 'E'
    },
    'O': {
        'class': 'secondary',
        'html': '&Omega;'
    }
}


class AmbulanceMap(TemplateView):
    template_name = 'ambulance/map.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ambulance_status'] = {m.name: m.value
                                       for m in AmbulanceStatus}
        context['ambulance_status_order'] = [m.name for m in AmbulanceStatusOrder]
        context['ambulance_capability'] = {m.name: m.value
                                           for m in AmbulanceCapability}
        context['ambulance_capability_order'] = [m.name for m in AmbulanceCapabilityOrder]
        context['location_type'] = {m.name: m.value
                                    for m in LocationType}
        context['location_type_order'] = [m.name for m in LocationTypeOrder]
        context['call_status'] = {m.name: m.value
                                  for m in CallStatus}
        context['call_status_order'] = [m.name for m in CallStatusOrder]
        context['call_priority'] = {m.name: m.value
                                    for m in CallPriority}
        context['call_priority_order'] = [m.name for m in CallPriorityOrder]
        context['ambulancecall_status'] = {m.name: m.value
                                           for m in AmbulanceCallStatus}
        context['broker_websockets_host'] = settings.MQTT['BROKER_WEBSOCKETS_HOST']
        context['broker_websockets_port'] = settings.MQTT['BROKER_WEBSOCKETS_PORT']
        context['client_id'] = 'javascript_client_' + uuid.uuid4().hex
        context['ambulance_css'] = AmbulanceCSS
        context['call_priority_css'] = CallPriorityCSS
        return context


# Locations

class LocationAdminListView(ListView):
    model = Location
    queryset = Location.objects.exclude(type=LocationType.h.name).exclude(type=LocationType.w.name)


class LocationAdminDetailView(DetailView):
    model = Location
    queryset = Location.objects.exclude(type=LocationType.h.name).exclude(type=LocationType.w.name)


class LocationAdminCreateView(SuccessMessageMixin,
                              UpdatedByMixin,
                              CreateView):
    model = Location
    form_class = LocationAdminCreateForm

    def get_success_message(self, cleaned_data):
        return "Successfully created location '{}'".format(cleaned_data['name'])

    def get_success_url(self):
        return self.object.get_absolute_url()


class LocationAdminUpdateView(SuccessMessageMixin,
                              UpdatedByMixin,
                              UpdateView):
    model = Location
    form_class = LocationAdminUpdateForm

    def get_success_message(self, cleaned_data):
        return "Successfully updated location '{}'".format(cleaned_data['name'])

    def get_success_url(self):
        return self.object.get_absolute_url()


# Calls

# Call permissions
class CallPermissionMixin(BasePermissionMixin):

    filter_field = 'ambulancecall__ambulance_id'
    profile_field = 'ambulances'
    queryset = Call.objects.all()


# Call ListView
class CallListView(LoginRequiredMixin,
                   CallPermissionMixin,
                   ListView):
    model = Call

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        context['pending_list'] = queryset.filter(status=CallStatus.P.name).order_by('pending_at')
        context['started_list'] = queryset.filter(status=CallStatus.S.name).order_by('-started_at')
        context['ended_list'] = queryset.filter(status=CallStatus.E.name).order_by('-started_at')
        return context


# Call DetailView
class CallDetailView(LoginRequiredMixin,
                     CallPermissionMixin,
                     SuccessMessageMixin,
                     UpdatedByMixin,
                     DetailView):
    model = Call

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ambulance_status'] = {m.name: m.value
                                       for m in AmbulanceStatus}
        return context

    def get_success_url(self):
        return self.object.get_absolute_url()


# Call abort view
class CallAbortView(LoginRequiredMixin,
                    CallPermissionMixin,
                    SuccessMessageMixin,
                    BaseDetailView):
    model = Call

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get(self, request, *args, **kwargs):

        # get call object
        self.object = self.get_object()

        # abort call
        self.object.abort()

        return redirect('ambulance:call_list')

# Admin page
# class AdminView(ListView):
#    model = Call
#   template_name = 'ambulance/dispatch_list.html'
#    context_object_name = "ambulance_call"


# # AmbulanceStatus list page
# class AmbulanceStatusCreateView(CreateView):
#     model = AmbulanceStatus
#     context_object_name = "ambulance_status_form"
#     form_class = AmbulanceStatusCreateForm
#     success_url = reverse_lazy('status')

#     def get_context_data(self, **kwargs):
#         context = super(AmbulanceStatusCreateView, self).get_context_data(**kwargs)
#         context['statuses'] = AmbulanceStatus.objects.all().order_by('id')
#         return context


# # AmbulanceStatus update page
# class AmbulanceStatusUpdateView(UpdateView):
#     model = AmbulanceStatus
#     form_class = AmbulanceStatusUpdateForm
#     template_name = 'ambulances/ambulance_status_edit.html'
#     success_url = reverse_lazy('status')

#     def get_object(self, queryset=None):
#         obj = AmbulanceStatus.objects.get(id=self.kwargs['pk'])
#         return obj

#     def get_context_data(self, **kwargs):
#         context = super(AmbulanceStatusUpdateView, self).get_context_data(**kwargs)
#         context['id'] = self.kwargs['pk']
#         return context


# # Ambulance map page
# class AmbulanceMap(views.JSONResponseMixin, views.AjaxResponseMixin, ListView):
#     template_name = 'ambulances/ambulance_map.html'

#     def get_queryset(self):
#         return Ambulance.objects.all()
